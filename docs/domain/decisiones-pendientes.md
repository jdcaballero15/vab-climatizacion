# Decisiones pendientes

No se asume nada de lo que figura acá. Cómo se refleja en las historias:

- **Decisión abierta** (`Abierta`): las historias afectadas llevan `blocked_by: [D-0XX]` y no pueden pasar a `ready` hasta resolverla.
- **Propuesta vigente** (`Propuesta` o `Pospuesta`): las historias llevan `assumes: [D-0XX]`. Se pueden implementar sobre la propuesta, sabiendo que si cambia hay que retocarlas.

El índice [docs/stories/INDEX.md](../stories/INDEX.md) lista las historias bloqueadas por decisión.

| ID | Decisión | Quién resuelve | Estado | Afecta |
|---|---|---|---|---|
| D-001 | Conectividad en campo: ¿hace falta modo offline? | Cliente | Resuelta | E99-06 a E99-08, E05-13, ADR 0003, ADR 0009 |
| D-002 | Identificación de equipos: código propio o por ubicación | Negocio | **Propuesta** | E03-03, E03-05, E04-12, E07-03, E07-09, E11-02, E11-06 |
| D-003 | Edición de catálogos en el sistema nuevo | Negocio | **Propuesta** | E02-01 a E02-06, E02-08 |
| D-004 | Datos exactos que necesita administración para facturar | Negocio | Pospuesta | E04-09 |
| D-005 | Revisión y aprobación en bloque: ¿acciones o estados? | Negocio | **Propuesta** | E04-08, E07-04, E07-05 |
| D-006 | Costo recurrente de hosting y cómo se informa al cliente | Dirección de MendoData | **Abierta** | E00-05 |
| D-007 | Método de inicio de sesión | Desarrollo y negocio | **Propuesta** | E01-01 |
| D-008 | Retención y texto legal de datos personales (DNI y firmas) | Negocio y asesoría legal | **Abierta** | E12-04 |
| D-009 | Proveedor de mail transaccional | Desarrollo | **Abierta** | E00-10 |
| D-010 | Formato y calidad de la exportación de Persat | Cliente y desarrollo | Resuelta | E11-01 a E11-04 |
| D-011 | ¿La firma del cliente es obligatoria en todo cierre? | Negocio | Resuelta | E05-07, E06-04, E06-06 |
| D-012 | Cierre de los issues de historias terminadas | Desarrollo | **Propuesta** | `scripts/sync_stories.py`, plantilla de PR |
| D-013 | Trabajo por escuadrillas en vez de técnico individual | Cliente | Resuelta | E02-09, E04-03, E04-04, E04-05, E04-08, E05-01, E05-02, E06-03, E08-01, E10-02 |

## Detalle

### D-001 Conectividad en campo

Los formularios del cliente se contradicen: "siempre hay señal" contra "a veces no, en cámaras frigoríficas, sótanos y zonas rurales". Mientras tanto, la PWA se diseñó con soporte offline (ADR 0003, provisional).

**Resuelta** (Gonza, 2026-10-26, con el relevamiento del cliente): las cuadrillas siempre tienen señal, y por eso el diseño original ya había descartado el modo offline. Para la versión 1.0 la app del técnico funciona solo con conexión. Mínimo de seguridad: si se corta la conexión con un cierre a medio cargar, lo cargado no se pierde (borrador en el celular) y se envía al volver la señal (E05-13). El offline completo queda fuera de la 1.0: las tres historias de offline de la épica E05 pasan al icebox (E99-06, E99-07 y E99-08). Ver ADR 0009, que reemplaza al 0003.

### D-002 Identificación de equipos

Contradicción en los formularios: "código propio" contra "por ubicación dentro del cliente". No es una cosa o la otra: se usan las dos, para fines distintos.

Lo que se sabe (relevamiento de Gonza con los datos de Persat):

- **La gente se refiere al equipo por su ubicación dentro del cliente** (por ejemplo "Habitación 12" u "Oficina planta alta"). Es lo que reconoce el técnico y el cliente pidió explícitamente que se vea así. En Persat, al cerrar una orden, el técnico describe el equipo a mano con ubicación, subtipo, marca y potencia.
- **Existe un código interno de VAB**, guardado en Persat en la columna de número de serie (no es el número de serie de fábrica). Se arma con un prefijo, el número de cliente y un correlativo del equipo dentro del cliente (por ejemplo `EA0012301` = cliente 00123, equipo 01). La intención es que sea único en toda la empresa, pero no está controlado: hay unos pocos códigos repetidos entre clientes distintos.
- **El código no tiene largo fijo.** La estructura real es `[EA|EH]` + sigla de sector (opcional) + número de cliente + correlativo:
  - `EA` es equipo de aire acondicionado y `EH` es heladera (hoy solo en un cliente).
  - Las siglas de sector (unas ocho distintas) aparecen solo en un cliente con planta industrial, por ejemplo `EAFAB` + número de cliente + correlativo. Se cree que son sectores de la planta, sin confirmar.
  - Hay dos excepciones de formato viejo: un cliente con `EACAB` + correlativo sin número de cliente y otro con `CLI-` + número de cliente + correlativo.
  - El correlativo empieza en 2 dígitos y pasa a 3 al superar 99 (el equipo 100 de un cliente lleva `100`, sin rellenar los anteriores). Hay clientes con más de 100 equipos y varios con más de 60.
  - El número de cliente dentro del código no tiene una cantidad fija de dígitos.
- **Persat trae unos 530 equipos de unos 55 clientes.** Algunas decenas no tienen ubicación, unos 20 no tienen ningún dato y ninguno tiene número de serie de fábrica.
- **En casi 9 de cada 10 reparaciones de Persat no se eligió el equipo cargado**: el técnico lo describió a mano. El caso "el equipo no está cargado" es frecuente.
- **Los equipos se mueven dentro del cliente**: existe el trabajo de reubicación de unidad condensadora o evaporadora.
- **El número de cliente de Persat es texto, no un número**: conviven una serie numérica de 5 dígitos y una serie `CLI-` + 5 dígitos, y hay algunos sueltos con otro formato o sin número.

*Propuesta*:

1. **Código interno (`internal_code`)**: identificador único en toda la empresa, obligatorio y generado por el sistema, nunca escrito a mano. Es texto libre: no se valida por largo ni por formato, porque los códigos migrados no son parejos.
   - **Equipos nuevos**: prefijo según el tipo de equipo (`EA` aire acondicionado, `EH` heladera) + dígitos del número de cliente + correlativo del equipo dentro del cliente, con mínimo 2 dígitos y sin tope (01 a 99, después 100, 101...). Sin sigla de sector hasta que el cliente confirme qué son.
   - **Unicidad**: la garantiza una restricción en la base, no el formato. Como los largos son variables, dos combinaciones distintas podrían dar el mismo texto; si el código generado ya existe, el sistema prueba el siguiente correlativo.
   - **Equipos migrados**: conservan su código de Persat tal cual, con el formato que tengan. A los códigos repetidos se les asigna uno nuevo en la migración y el viejo queda como referencia a Persat.
2. **Ubicación (`location_note`)**: obligatoria. Es lo que se muestra primero en listados, órdenes y comprobantes, junto con el tipo de equipo. Dentro de un mismo domicilio no hay unicidad: pueden existir dos equipos con la misma ubicación (por ejemplo, dos splits en el mismo salón) y los distingue el código.
3. **Alta con lo mínimo**: para dar de alta un equipo alcanza con ubicación y tipo de equipo. Marca, modelo, potencia y el resto son opcionales y administración los completa después.
4. **Mudanzas**: si un equipo cambia de ubicación dentro del cliente, se edita la ubicación. Conserva su código y su historial; no se crea un equipo nuevo.
5. **Migración**: los equipos de Persat sin ubicación se importan con la ubicación "Sin ubicación" y quedan en el informe de calidad (E11-04) para que administración la complete.

Consecuencias:

- El cliente necesita un **número de cliente** (`client.number`), porque forma parte del código. Es texto y único. En la migración se toma el número de Persat tal cual; los clientes sin número reciben uno nuevo. En los clientes nuevos lo asigna el sistema siguiendo la serie numérica (el siguiente al máximo).
- El técnico no da de alta equipos desde la app: lo confirmó el cliente el 2026-10-28 (los carga solo la oficina).
- El QR por equipo (E99-01) sigue en el icebox; si vuelve, se apoya en el código interno.

Respondido por Gonza (2026-10-26, refinamiento de E03-03):

- **Un prefijo por tipo de equipo**: `EA` aire acondicionado, `EH` heladera comercial y familiar, `EC` cámara de frío, `EF` freezer y `EO` otros. Un tipo nuevo usa `EO` hasta que se le asigne uno.
- **Un equipo puede pasar a otro domicilio del mismo cliente**, además de cambiar de ubicación, y conserva código e historial.
- Datos opcionales del equipo: marca, modelo, número de serie de fábrica y observaciones.

Respondido por el cliente (2026-10-28):

- **No hay etiquetas pegadas en los equipos.** Según el cliente, el único que hoy usa los códigos es un cliente industrial (el de las siglas de sector). El código lo sigue generando el sistema; en el resto de los clientes la gente identifica el equipo por la ubicación (confirmado por Gonza el mismo día).
- **El técnico no da de alta equipos.** Los carga solo la oficina, para no tener repetidos con distinto nombre. Si la escuadrilla encuentra un equipo que no está cargado, lo avisa (por ejemplo, en la observación del cierre).
- **Un equipo puede pasar de un cliente a otro** (venta o traslado). Va en una historia nueva, E03-09 (`draft`).

Preguntas abiertas para el cliente:

- ¿Las siglas como `FAB` son sectores de la planta? ¿Hay que seguir usándolas en los equipos nuevos de ese cliente?

Respondido por Gonza (2026-10-28): al pasar a otro cliente el equipo **recibe un código nuevo** con el número del cliente nuevo, y queda registro del traslado y del código anterior (E03-09).

### D-003 Edición de catálogos

La decisión original era sobre listas de SharePoint ("editables de las dos formas" con columnas de elección). En un sistema a medida **ese problema desaparece**: la única puerta de entrada es la app, con las mismas validaciones.
*Propuesta*: los catálogos y listas de referencia (tipos de trabajo, tareas, fallas, reparaciones, repuestos, plantillas) se editan solo desde la app de administración, con importación y exportación CSV para cargas masivas. El estado de la orden y todo lo que dispara automatizaciones solo cambia por la API.

### D-004 Datos para facturar

Se pospone. El modelo guarda número de factura y fecha de registro (`invoice_record`). Si administración necesita más (importe, condición de venta, CUIT), se agrega.

### D-005 Revisión y aprobación en bloque

El cliente definió siete estados y no incluye "Revisión" ni "Pendiente de aprobación". La propuesta técnica los muestra como pasos del circuito.
*Propuesta*: no son estados. Son acciones de administración: aprobar o devolver una orden Terminada, y aprobar un lote de órdenes generadas (campo `requires_approval`). Si el cliente prefiere verlos como estados, se agregan.

### D-006 Costo recurrente de hosting

Con Microsoft 365 no había costo de infraestructura. Con el sistema a medida hay un costo mensual en dólares. Hay que definir cómo se informa y se cobra al cliente (referencia con cotización y fecha, o dentro de un abono de soporte). Las cuentas quedan a nombre del cliente. **Este tema se gestiona fuera del repositorio.**

### D-007 Método de inicio de sesión

*Propuesta*: correo y contraseña con política mínima, sesión por JWT de corta duración con refresco, límite de intentos. Evaluar más adelante inicio con cuenta Microsoft o Google si el cliente lo pide.

### D-008 Datos personales

El sistema guarda nombre y DNI de quien firma, y la firma manuscrita. Definir: plazo de retención, derecho de acceso y supresión, aviso en el comprobante, y si hace falta registrar la base ante la autoridad de aplicación. Consultar a asesoría legal.

*Avance* (Gonza, 2026-10-28): en el cierre de una orden **no se pide el DNI**, solo el nombre de quien firma y la firma (E05-07). Falta confirmar si vale también para retiro y devolución (E06-04, E06-06). Siguen abiertos la retención de firmas y nombres y el aviso legal.

### D-009 Proveedor de mail

Para informe mensual y comprobantes. Candidatos: Resend, Brevo, Amazon SES. Criterios: entregabilidad, costo, dominio propio del cliente (SPF, DKIM).

### D-011 Obligatoriedad de la firma

Los formularios del cliente dicen que la firma es obligatoria al cerrar una orden. La propuesta técnica, en cambio, dice "firma del cliente, si corresponde" para las órdenes en el lugar, y la exige solo en retiro y devolución.
*Propuesta*: seguir lo que dicen los formularios (firma obligatoria en todo cierre, con nombre y DNI), y que negocio defina qué pasa si el cliente no está presente (por ejemplo, un motivo de ausencia predefinido). No se inventa una excepción hasta que se defina.

**Resuelta** (Gonza, 2026-10-28): todo cierre lleva la firma del cliente o un motivo por el que no hay. Motivos propuestos: "Cliente ausente", "No quiso firmar" y "Otro" con texto (a validar con la oficina). Ver E05-07.

### D-010 Exportación de Persat

El cliente confirmó que es exportable. Faltaba ver el formato real, qué campos trae el historial de trabajos y la calidad de los datos. **La muestra no se sube al repo.**

**Resuelta** (Gonza, 2026-10-26, con la exportación del 2026-10-08): clientes, equipos y repuestos vienen en `.xlsx`; las órdenes, un archivo por formulario en `.xls` que en realidad es HTML con tablas anidadas. El importador lee la **exportación cruda** y aplica las reglas de limpieza, porque la migración real se hace con una exportación nueva justo antes de salir. Las decisiones puntuales sobre registros reales van en un archivo de decisiones de migración fuera del repo. El detalle de archivos, columnas y reglas está en [migracion-persat.md](migracion-persat.md).

Queda abierto: no hay historia para importar repuestos y servicios de Persat (302 repuestos sin precio y 84 servicios). Hay que decidir si entran por la importación de catálogos (E02-08) o por una historia nueva de E11.

### D-012 Cierre de los issues de historias terminadas

Hoy ningún issue de historia se cierra solo. `sync_stories.py` actualiza la etiqueta `estado:hecha` pero, por diseño, nunca cierra issues. La plantilla de PR usa `Cierra #`, que GitHub no reconoce como palabra clave de cierre (solo acepta las de inglés, como `Closes` o `Fixes`). Resultado: E01-01 (#21), E01-02 (#22), E01-03 (#23) y E01-04 (#24) están terminadas y sus issues siguen abiertos, lo que ensucia la vista de issues abiertos como lista de trabajo pendiente.

Opciones:

1. **`Closes #` en la plantilla de PR**: el issue se cierra al mergear la PR en `main`. No sirve cuando una historia se entrega en varias PR (como E01-02): la primera PR cerraría el issue antes de tiempo, o hay que acordarse de ponerlo solo en la última.
2. **Que `sync_stories.py` cierre el issue cuando la historia pasa a `done`** (y lo reabra si vuelve a otro estado): el cierre queda atado al archivo de la historia, que ya es la fuente de verdad, y funciona igual con una o varias PR. Al correr por primera vez cerraría los issues de las historias ya terminadas.

*Propuesta*: opción 2. En la plantilla, cambiar `Cierra #` por `Relacionado #` para que no parezca que cierra algo. Si se aprueba, se implementa en una PR aparte que actualice el script, su docstring y la plantilla.

### D-013 Trabajo por escuadrillas

El prototipo que armó el cliente (2026-10-26) asigna las órdenes a **escuadrillas**, no a técnicos. Contradice lo decidido en E04-01 y E04-03 ("un solo técnico responsable por orden").

*Resuelta con negocio el 2026-10-26*:

- Las escuadrillas son una **lista fija con nombre** que carga administración ("Escuadrilla 1", "Escuadrilla 2"…). Van de a 2 personas, pero **las personas cambian**: lo fijo es la escuadrilla, no quiénes la forman.
- **Un usuario por celular**: cada escuadrilla tiene su usuario de la app (rol `technician`). Quienes salen ese día usan ese celular.
- Los **técnicos** son una lista de personas de campo, sin usuario. **Al cerrar una orden se tilda quiénes fueron**; de ahí salen los trabajos por técnico (E10-02).
- Una orden (o una etapa, en taller) tiene **una sola escuadrilla responsable** (R7).
- Las demás diferencias con el prototipo se revisan una por una, en otras decisiones.

