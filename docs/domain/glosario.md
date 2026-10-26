# Glosario

Los términos de negocio van en español. Entre paréntesis, el nombre usado en el código.

| Término | Significado |
|---|---|
| **Orden de trabajo, OT** (`work_order`) | Unidad de trabajo que viaja desde el pedido hasta el cobro |
| **Orden en el lugar** (`on_site`) | OT de una sola etapa que el técnico cierra en el domicilio del cliente |
| **Orden de taller** (`workshop`) | OT con tres etapas: retiro, taller y devolución |
| **Etapa** (`work_order_stage`) | Tramo de una orden de taller. Cada una puede hacerla una escuadrilla distinta |
| **Escuadrilla** (`crew`) | Equipo de campo, normalmente de a 2, con nombre fijo y un celular con su usuario. Las personas que la forman cambian (D-013) |
| **Técnico** (`field_technician`) | Persona de campo. No tiene usuario: se tilda al cerrar las órdenes en las que fue |
| **Estado** (`status`) | Pendiente, Asignada, En curso, Terminada, Facturada, Cobrada, Cancelada |
| **Revisión** | Control de administración sobre una orden Terminada antes de facturar |
| **Cierre** (`work_order_closure`) | Registro que hace la escuadrilla al terminar: quiénes fueron, falla, reparación, repuestos, foto, observación, firma |
| **Falla** (`failure`) | Problema encontrado, elegido de una lista por tipo de equipo |
| **Reparación** (`repair`) | Solución aplicada, elegida de una lista |
| **Otro** | Opción de cierre que exige observación. Los textos repetidos se pueden promover a la lista |
| **Tipo de trabajo** (`work_type`) | Instalación, reparación, service, devolución, retiro, relevamiento |
| **Tarea** (`task`) | Subtarea predefinida de un tipo de trabajo |
| **Equipo** (`equipment`) | Aparato del cliente sobre el que se trabaja (aire acondicionado, cámara, etc.) |
| **Sitio** (`client_site`) | Domicilio o sucursal de un cliente donde hay equipos |
| **Abonado, abono** (`maintenance_plan`) | Cliente con contrato de mantenimiento mensual que incluye ciertos equipos |
| **Mantenimiento preventivo** | Visita programada con checklist según frecuencia y tipo de equipo |
| **Checklist** (`checklist_template`) | Lista de tareas OK o No OK y mediciones con rango esperado |
| **Medición** | Valor numérico (tensión, consumo) con unidad y rango. Fuera de rango obliga a observación |
| **Corrida de mantenimiento** (`maintenance_run`) | Generación mensual automática de las órdenes de los abonados |
| **Aprobación en bloque** | Administración aprueba todas las órdenes generadas de un mes de una vez |
| **Repuesto, material** (`part`) | Pieza que se usa en un trabajo. Hoy sin código |
| **Depósito, camioneta** (`stock_location`) | Ubicaciones donde hay stock de repuestos |
| **Movimiento de stock** (`stock_movement`) | Ingreso, transferencia, uso o ajuste. El stock es la suma de movimientos |
| **Precio estampado** | Precio del repuesto guardado en el momento de usarlo |
| **Comprobante** | PDF de retiro o devolución con la firma, para enviar al cliente |
| **Informe mensual** | Mail mensual a cada cliente con los trabajos realizados |
| **Persat** | Sistema actual a reemplazar. Se exporta clientes, equipos e historial |
| **Convivencia** | Período en que se usa el sistema nuevo y Persat en paralelo hasta la baja de Persat |
