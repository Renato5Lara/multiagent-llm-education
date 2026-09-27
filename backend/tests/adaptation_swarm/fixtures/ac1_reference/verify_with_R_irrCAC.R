# CERTIFICACIÓN PX8 (PENDIENTE DE EJECUCIÓN): calcula Gwet AC1 con el paquete R `irrCAC` original para los casos del fixture y guarda la evidencia.
# NO se ha ejecutado nunca (R no estaba disponible cuando se preparó este script): los nombres de campo de `gwet.ac1.raw` siguen la documentación de irrCAC y se COMPRUEBAN al ejecutar.
#
# Uso (desde este directorio):  Rscript verify_with_R_irrCAC.R ac1_reference_cases.json r_irrCAC_results.json
# Requiere:  install.packages(c("irrCAC", "jsonlite"))   — se registran las versiones reales de R y de irrCAC; no se exige una versión mínima concreta.
# Salida (r_irrCAC_results.json): versión de R, versión de irrCAC, función usada, hash del archivo de entrada, campos devueltos por gwet.ac1.raw, sessionInfo y, por caso, id/ac1/pa/pe con la PRECISIÓN COMPLETA
# que devuelva R (digits = NA): el test `test_panel_archetypes.py::test_ac1_certification_against_R_irrCAC` deriva su tolerancia de los decimales que R realmente entregue (no de una suposición).
suppressPackageStartupMessages({ library(irrCAC); library(jsonlite) })
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 2)
spec <- fromJSON(args[1], simplifyVector = FALSE)

file_hash <- function(path) {                       # sha256 si esta versión de R lo ofrece (tools::sha256sum, R >= 4.5); si no, md5 (base R). Se guarda el algoritmo usado.
  if (exists("sha256sum", envir = asNamespace("tools"), inherits = FALSE)) list(algo = "sha256", value = unname(tools::sha256sum(path)))
  else list(algo = "md5", value = unname(tools::md5sum(path)))
}

est_names <- NULL
cases <- lapply(spec$cases, function(cs) {
  n <- cs$n; ks <- unlist(cs$approvals)
  ratings <- sapply(seq_len(n), function(j) ifelse(j <= ks, 1, 0))     # filas = ítems (4 arquetipos), columnas = evaluadores; 1 = Aprobar, 0 = Rechazar
  est <- gwet.ac1.raw(as.data.frame(ratings), weights = "unweighted")$est
  if (is.null(est_names)) est_names <<- names(est)
  stopifnot(all(c("coeff.val", "pa", "pe") %in% names(est)))          # falla si irrCAC no devuelve los campos esperados: NO se adivina otro nombre
  list(id = cs$id, ac1 = est$coeff.val, pa = est$pa, pe = est$pe)
})

write_json(list(
  source = "R irrCAC (paquete original)", r_version = R.version.string, irrCAC_version = as.character(packageVersion("irrCAC")),
  function_used = "irrCAC::gwet.ac1.raw(ratings, weights = 'unweighted')", input_file = basename(args[1]), input_hash = file_hash(args[1]),
  est_fields = est_names, session_info = capture.output(sessionInfo()), cases = cases),
  args[2], auto_unbox = TRUE, digits = NA, pretty = TRUE)
