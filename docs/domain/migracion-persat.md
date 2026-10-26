# Migración desde Persat

Cómo se leen y se limpian los datos de Persat al importarlos (épica E11). Resume la decisión `D-010`.

**Ningún archivo de Persat ni de decisiones de migración se sube al repo.** Tienen datos reales de clientes. Se guardan fuera del repo (o en `persat-export/`, que está en `.gitignore`) y se le pasan al importador por parámetro.

## Principio

El importador lee la **exportación cruda** de Persat y le aplica las reglas de limpieza de esta página. No lee una planilla ya limpia: la migración real se hace con una exportación nueva justo antes de salir, porque Persat sigue en uso hasta entonces. La limpieza tiene que poder repetirse sobre cualquier exportación.

Las reglas generales viven en el código del importador. Las decisiones puntuales sobre registros reales (qué registros no se migran, qué códigos repetidos se reasignan, qué clientes duplicados se unifican) van en un **archivo de decisiones de migración** aparte, fuera del repo, que el importador lee si existe.

Las reglas salen de los scripts con los que Gonza armó la planilla limpia (pandas y BeautifulSoup). Esos scripts son la especificación, no código para copiar.

## Archivos de la exportación

| Archivo | Formato | Contenido |
|---|---|---|
| Clientes | `.xlsx`, una hoja, 17 columnas | Nro. de Cliente, Razón Social, Descripción, Tipo, Grupo, Dirección, Latitud, Longitud, Inicio de Jornada, Fin de Jornada, Tiempo de Servicio, Nombre, Email, Telefono, Altura, Localidad, Provincia |
| Equipos | `.xlsx`, 11 columnas | Numero de Serie (es el código interno, ver `D-002`), Nro. de Cliente, Razón Social, UBICACION, TIPO, SUB TIPO, MODELO, MARCA, POTENCIA, GAS REFRIGERANTE, TENSION DE ALIMENTACION |
| Repuestos y servicios | `.xlsx` | Nro. Identificacion, DESCRIPCION, UNIDAD DE MEDIDA, CANTIDAD, Precio (sin precios cargados). Los servicios (códigos `S` + número) vienen mezclados con los repuestos; hay además un archivo de servicios aparte |
| Órdenes | Un archivo por formulario (10 formularios) | `.xls` que en realidad son HTML, con 25 a 49 columnas según el formulario. Varias celdas traen tablas anidadas (datos del equipo, materiales, checklist) |

Las órdenes tienen 14 columnas comunes a todos los formularios, entre ellas: número, estado, fecha, causa de cierre, cliente, número de cliente, tipo, grupo, tipo de formulario (nombre y versión), etiquetas (tipo de trabajo y técnicos) y técnico (la cuadrilla).

## Reglas de limpieza

Generales: se recortan los espacios de más en todos los textos.

### Clientes

- **No se migran** los registros internos (tipo operario, depósito o administración) ni los registros de prueba de Persat.
- **Número de cliente**: es texto (ver `D-002`). Se corrigen los espacios alrededor del guion (`CLI -123` pasa a `CLI-123`). Un cliente sin número recibe uno nuevo y queda para revisar.
- **Segmento**: sale de la columna Tipo (particular, comercio, estado, sanatorio o clínica, hotel; el resto, sin clasificar).
- **Localidad**: se toma de la dirección cuando la dirección termina en el país; si no, de la columna Localidad.
- **Coordenadas**: muchas son inválidas (valores fuera de rango, como una longitud de nueve dígitos). Solo se conservan las que caen dentro de la región de trabajo; para ubicar al cliente se usa la dirección.
- **Email** en minúsculas. **Teléfono** como texto, sin decimales.
- Sin dirección: queda para revisar.

### Equipos

- **Tipo de equipo**: si el tipo dice heladera, es heladera comercial, o heladera familiar si el subtipo es frigobar (queda para confirmar). En cualquier otro caso es aire acondicionado; si el tipo venía vacío, queda para revisar.
- **Subtipo**: se unifican las variantes y errores de tipeo (split, split inverter, piso techo, rooftop, bajo silueta, compacto, cassette, ventana, frigobar, comercial).
- **Función**: la columna MODELO en realidad dice frío solo o frío/calor.
- **Marca**: se unifican mayúsculas y se corrigen errores de tipeo con una tabla de correcciones. Las siglas (como BGH o LG) quedan en mayúsculas. Un número en la columna marca no es una marca.
- **Columnas corridas**: si el subtipo trae una marca, se mueve a marca y la capacidad que estaba en marca pasa a capacidad.
- **Gas**: se unifica el formato (R-22, R-410A, R-404A, R-134a, R-32). Algunos valores son errores de arrastre de una planilla (411, 413, 414, 415) y se toman como R-410A, para revisar.
- **Capacidad**: se separa en número y unidad (frigorías, TR o W). `3000FG`, `3000FRG` y `3000` son 3000 frigorías.
- **Tensión**: 220 V o 380 V.
- **Código interno**: se conserva el de Persat tal cual. Los códigos repetidos en más de un equipo reciben uno nuevo (`D-002`). Sin ubicación: se importa con "Sin ubicación". Sin ningún dato: queda para revisar.
- Todo equipo tiene que apuntar a un cliente importado.

### Repuestos y servicios

- Los códigos que empiezan con `S` son servicios y se separan de los repuestos.
- Descripciones con errores de tipeo corregidos y en formato oración. Unidad de medida unificada (unidad, metro, litro, kg).
- Los servicios repetidos (misma descripción) se unifican y queda uno solo. Los códigos de servicio sin la `S` son de un formato viejo y quedan para revisar.

### Órdenes (historial)

- Cada archivo es una tabla HTML: los encabezados salen del `thead` y cada fila del cuerpo es una orden. Las celdas con tablas anidadas se leen como filas y columnas.
- **Tipo de trabajo**: según el formulario (reparación, visita de reparación, retiro, devolución, instalación, preinstalación, relevamiento y tres de mantenimiento).
- **Estado de Persat**: hecha sin cerrar, cerrada, vencida, cerrada no cumplida, cancelada o asignada.
- **Técnicos**: salen de las etiquetas, descartando las que son tipos de trabajo. **Cuadrilla**: el número de la columna técnico.
- **Equipo**: el código de la celda de datos del equipo, salvo que diga `N/A` o esté vacío (pasa en casi 9 de cada 10 reparaciones).
- **Detalle**: se juntan los textos de reclamo, observación, trabajo realizado, falla detectada, causal de retiro y tareas, sin repetir y sin valores de relleno (`0`, `N/A`, `OTROS`).

## Resultado esperado

La importación sobre la exportación del 2026-10-08 tiene que dar **632 clientes, 532 equipos, 302 repuestos, 84 servicios y 1.743 órdenes**, igual que la planilla limpia. Es una verificación manual con los archivos reales, fuera del CI. Los tests automáticos usan archivos ficticios con el mismo formato.
