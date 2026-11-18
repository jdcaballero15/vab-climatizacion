import { api } from "../../api/client";
import type { components } from "../../api/schema";

export type Kind = components["schemas"]["PromoteRequest"]["kind"];
export type OtherText = components["schemas"]["OtherTextOut"];

export const KINDS: Record<Kind, string> = {
  failure: "Fallas",
  repair: "Reparaciones",
  part: "Materiales",
};
export const OTHER_TEXTS_KEY = ["other-texts"] as const;
export const OTHER_TEXT_KINDS = Object.keys(KINDS) as Kind[];

export function otherTextsQuery(kind: Kind) {
  return {
    queryKey: [...OTHER_TEXTS_KEY, kind],
    queryFn: async (): Promise<OtherText[]> => {
      const { data, error } = await api.GET("/admin/other-texts", {
        params: { query: { kind } },
      });
      if (error || !data) {
        throw new Error("no se pudieron cargar los textos");
      }
      return data;
    },
  };
}
