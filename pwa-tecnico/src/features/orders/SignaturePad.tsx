import { Eraser } from "lucide-react";
import { useEffect, useRef, type PointerEvent } from "react";

// Tamaño fijo del dibujo: el lienzo se estira con CSS, así girar el celular no cambia el
// trazo ni hace falta redibujarlo, y el PNG queda chico.
const WIDTH = 600;
const HEIGHT = 240;
const LINE_WIDTH = 3;

interface SignaturePadProps {
  /** La firma guardada en el borrador (E05-13), para mostrarla al volver. */
  blob: Blob | null;
  disabled: boolean;
  invalid: boolean;
  /** PNG nuevo al terminar cada trazo, o `null` al borrar. */
  onChange: (blob: Blob | null) => void;
}

/** Firma del cliente con el dedo, un lápiz o el mouse (E05-07). */
export function SignaturePad({ blob, disabled, invalid, onChange }: SignaturePadProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  // El blob que muestra el lienzo: el que llega de afuera después de un trazo es el mismo.
  const shown = useRef<Blob | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context || blob === shown.current) {
      return;
    }
    shown.current = blob;
    context.clearRect(0, 0, WIDTH, HEIGHT);
    if (blob && typeof createImageBitmap === "function") {
      void createImageBitmap(blob).then((bitmap) => {
        if (shown.current === blob) {
          context.drawImage(bitmap, 0, 0, WIDTH, HEIGHT);
        }
        bitmap.close();
      });
    }
  }, [blob]);

  const pointAt = (event: PointerEvent<HTMLCanvasElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    return {
      x: ((event.clientX - box.left) * WIDTH) / (box.width || WIDTH),
      y: ((event.clientY - box.top) * HEIGHT) / (box.height || HEIGHT),
    };
  };

  const start = (event: PointerEvent<HTMLCanvasElement>) => {
    const context = event.currentTarget.getContext("2d");
    if (disabled || !context) {
      return;
    }
    event.currentTarget.setPointerCapture?.(event.pointerId);
    drawing.current = true;
    const { x, y } = pointAt(event);
    context.lineWidth = LINE_WIDTH;
    context.lineCap = "round";
    context.lineJoin = "round";
    context.strokeStyle = "#0f172a";
    context.beginPath();
    context.moveTo(x, y);
    // Un toque sin mover deja un punto.
    context.lineTo(x + 0.1, y + 0.1);
    context.stroke();
  };

  const move = (event: PointerEvent<HTMLCanvasElement>) => {
    const context = event.currentTarget.getContext("2d");
    if (!drawing.current || !context) {
      return;
    }
    const { x, y } = pointAt(event);
    context.lineTo(x, y);
    context.stroke();
  };

  const end = (event: PointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) {
      return;
    }
    drawing.current = false;
    event.currentTarget.toBlob((png) => {
      if (png) {
        shown.current = png;
        onChange(png);
      }
    }, "image/png");
  };

  const clear = () => {
    canvasRef.current?.getContext("2d")?.clearRect(0, 0, WIDTH, HEIGHT);
    shown.current = null;
    onChange(null);
  };

  return (
    <div className="signature">
      <canvas
        ref={canvasRef}
        width={WIDTH}
        height={HEIGHT}
        className={invalid ? "signature__pad signature__pad--invalid" : "signature__pad"}
        role="img"
        aria-label={blob ? "Firma del cliente" : "Espacio para la firma del cliente"}
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={end}
        onPointerCancel={end}
      />
      <div className="signature__footer">
        <span className="closure__hint">
          {blob ? "Firmado." : "Firmá con el dedo dentro del recuadro."}
        </span>
        <button
          type="button"
          className="signature__clear"
          disabled={disabled || !blob}
          onClick={clear}
        >
          <Eraser size={18} aria-hidden="true" />
          Borrar
        </button>
      </div>
    </div>
  );
}
