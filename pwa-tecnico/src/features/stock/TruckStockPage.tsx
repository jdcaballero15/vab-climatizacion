import { ArrowLeft } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../../api/client";

function quantityText(quantity: string): string {
  return Number(quantity).toLocaleString("es-AR", { maximumFractionDigits: 3 });
}

/**
 * Lo que lleva la camioneta de la escuadrilla (E08-04, criterio 4; E08-05, criterio 2),
 * sin precios. Lo usado en cada cierre se descuenta solo; un negativo quiere decir que se
 * usó más de lo cargado y la oficina lo ajusta.
 */
export function TruckStockPage() {
  const query = useQuery({
    queryKey: ["tech", "stock"],
    queryFn: async () => {
      const { data, error } = await api.GET("/tech/stock");
      if (error || !data) {
        throw new Error("No se pudo cargar la camioneta.");
      }
      return data;
    },
  });

  return (
    <main className="orders">
      <Link to="/" className="order-detail__back">
        <ArrowLeft size={18} aria-hidden="true" /> Mis órdenes
      </Link>
      <header className="orders__header">
        <p className="eyebrow">Stock</p>
        <h1>{query.data?.location_name ?? "Mi camioneta"}</h1>
      </header>
      {query.isLoading && <p className="orders__message">Cargando…</p>}
      {query.isError && (
        <p className="orders__message" role="alert">
          No se pudo cargar la camioneta. Revisá la conexión.
        </p>
      )}
      {query.data && query.data.location_name === null && (
        <p className="orders__message">
          Tu escuadrilla no tiene una camioneta cargada. Avisale a administración.
        </p>
      )}
      {query.data?.location_name && query.data.items.length === 0 && (
        <p className="orders__message">La camioneta no tiene repuestos cargados.</p>
      )}
      {query.data && query.data.items.length > 0 && (
        <ul className="orders__list" aria-label="Repuestos de la camioneta">
          {query.data.items.map((item) => (
            <li key={item.part_name} className="order-card">
              <strong>{item.part_name}</strong>{" "}
              <span>
                {quantityText(item.quantity)} {item.unit}
              </span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
