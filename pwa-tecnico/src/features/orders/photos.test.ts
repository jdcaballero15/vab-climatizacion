import { afterEach, describe, expect, it, vi } from "vitest";

import {
  PhotoUploadError,
  compressImage,
  scaledSize,
  uploadPhotos,
  type ClosurePhoto,
} from "./photos";

const FILE_ID = "f0000000-0000-4000-8000-000000000001";
const UPLOAD_URL = "https://bucket.example/ot-files/closure_photo/x?firma=1";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function photo(overrides: Partial<ClosurePhoto> = {}): ClosurePhoto {
  return {
    key: "p1",
    blob: new Blob(["foto"], { type: "image/jpeg" }),
    previewUrl: "blob:p1",
    fileId: null,
    uploaded: false,
    ...overrides,
  };
}

interface Call {
  method: string;
  url: string;
  body: unknown;
  contentType: string | null;
  authorization: string | null;
}

/** Simula la API de archivos y el bucket. `put` decide la respuesta del bucket. */
function stubFiles(
  put: () => Response = () => new Response(null, { status: 200 }),
  confirm: () => Response = () => json({ id: FILE_ID }),
) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: Request | string, init?: RequestInit) => {
      const request = input instanceof Request ? input : new Request(input, init);
      const isJson = request.headers.get("Content-Type") === "application/json";
      calls.push({
        method: request.method,
        url: request.url,
        body: isJson ? await request.json() : null,
        contentType: request.headers.get("Content-Type"),
        authorization: request.headers.get("Authorization"),
      });
      if (request.url === UPLOAD_URL) {
        return put();
      }
      if (request.url.endsWith("/confirm")) {
        return confirm();
      }
      return json({ file_id: FILE_ID, upload_url: UPLOAD_URL, expires_in: 300 }, 201);
    }),
  );
  return calls;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("scaledSize", () => {
  // E05-06, nota técnica: lado mayor de 1600 px, sin agrandar las chicas.
  it("achica el lado mayor a 1600 manteniendo la proporción", () => {
    expect(scaledSize(4000, 3000)).toEqual({ width: 1600, height: 1200 });
    expect(scaledSize(3000, 4000)).toEqual({ width: 1200, height: 1600 });
  });

  it("deja igual una foto que ya es chica", () => {
    expect(scaledSize(800, 600)).toEqual({ width: 800, height: 600 });
  });
});

describe("compressImage", () => {
  // E05-06, criterio 1: se comprime en el celular a JPEG de calidad 0,8.
  it("dibuja la foto achicada y la exporta como JPEG 0,8", async () => {
    const close = vi.fn();
    vi.stubGlobal(
      "createImageBitmap",
      vi.fn(async () => ({ width: 4000, height: 3000, close })),
    );
    const drawImage = vi.fn();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
      drawImage,
    } as unknown as CanvasRenderingContext2D);
    const toBlob = vi
      .spyOn(HTMLCanvasElement.prototype, "toBlob")
      .mockImplementation(function (callback) {
        callback(new Blob(["chica"], { type: "image/jpeg" }));
      });

    const result = await compressImage(new File(["grande"], "foto.jpg", { type: "image/jpeg" }));

    expect(result.type).toBe("image/jpeg");
    expect(drawImage).toHaveBeenCalledWith(expect.anything(), 0, 0, 1600, 1200);
    expect(toBlob).toHaveBeenCalledWith(expect.any(Function), "image/jpeg", 0.8);
    expect(close).toHaveBeenCalled();
  });

  it("avisa si el archivo no es una imagen que se pueda abrir", async () => {
    vi.stubGlobal(
      "createImageBitmap",
      vi.fn(async () => {
        throw new Error("no es imagen");
      }),
    );

    await expect(compressImage(new File(["x"], "a.txt"))).rejects.toBeInstanceOf(PhotoUploadError);
  });
});

describe("uploadPhotos", () => {
  // E05-06, criterio 3: pedir subida, PUT al bucket y confirmar, en ese orden.
  it("sube cada foto al bucket y devuelve los ids en orden", async () => {
    const calls = stubFiles();
    const saved: Partial<ClosurePhoto>[] = [];

    const ids = await uploadPhotos([photo()], (_key, changes) => saved.push(changes));

    expect(ids).toEqual([FILE_ID]);
    expect(calls.map((call) => [call.method, new URL(call.url).pathname])).toEqual([
      ["POST", "/api/files"],
      ["PUT", "/ot-files/closure_photo/x"],
      ["POST", `/api/files/${FILE_ID}/confirm`],
    ]);
    expect(calls[0].body).toEqual({
      purpose: "closure_photo",
      content_type: "image/jpeg",
      size_bytes: 4,
    });
    // El PUT va con el tipo firmado y sin el token de la API.
    expect(calls[1].contentType).toBe("image/jpeg");
    expect(calls[1].authorization).toBeNull();
    expect(saved).toEqual([{ fileId: FILE_ID }, { uploaded: true }]);
  });

  it("no vuelve a subir una foto ya confirmada", async () => {
    const calls = stubFiles();

    const ids = await uploadPhotos([photo({ fileId: FILE_ID, uploaded: true })], () => {});

    expect(ids).toEqual([FILE_ID]);
    expect(calls).toHaveLength(0);
  });

  // E05-06, criterio 5: un reintento no pierde ni duplica la foto.
  it("si falló solo la confirmación, reintenta confirmar sin volver a subir", async () => {
    const calls = stubFiles();

    const ids = await uploadPhotos([photo({ fileId: FILE_ID, uploaded: false })], () => {});

    expect(ids).toEqual([FILE_ID]);
    expect(calls.map((call) => call.method)).toEqual(["POST"]);
    expect(calls[0].url).toContain("/confirm");
  });

  it("con mala señal en el bucket, avisa y deja la foto para reintentar", async () => {
    stubFiles(() => {
      throw new TypeError("Failed to fetch");
    });
    const saved: Partial<ClosurePhoto>[] = [];

    await expect(
      uploadPhotos([photo()], (_key, changes) => saved.push(changes)),
    ).rejects.toMatchObject({ message: expect.stringContaining("conexión") });
    // No quedó un id a medias: el reintento pide una subida nueva.
    expect(saved).toEqual([]);
  });

  it("si el bucket no recibió el archivo, el reintento la sube de nuevo", async () => {
    stubFiles(undefined, () =>
      json(
        {
          detail: { code: "upload_missing", field: "file_id", message: "El archivo no llegó." },
        },
        422,
      ),
    );
    const saved: Partial<ClosurePhoto>[] = [];

    await expect(
      uploadPhotos([photo({ fileId: FILE_ID })], (_key, changes) => saved.push(changes)),
    ).rejects.toBeInstanceOf(PhotoUploadError);
    expect(saved).toEqual([{ fileId: null }]);
  });

  it("muestra el mensaje de la API si rechaza la foto", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        json(
          {
            detail: {
              code: "file_too_large",
              field: "size_bytes",
              message: "El archivo supera el máximo de 5 MB.",
            },
          },
          422,
        ),
      ),
    );

    await expect(uploadPhotos([photo()], () => {})).rejects.toMatchObject({
      message: "El archivo supera el máximo de 5 MB.",
    });
  });
});
