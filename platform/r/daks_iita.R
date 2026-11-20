# Inductive item tree analysis (DAKS::iita).
#
# Input:
#   responses  {"items": ["a", ...], "matrix": [[0, 1, ...], ...]}
#              respondents x items, binary, columns in item order
#   params     {"version": 1 | 2 | 3}          1 = minimized corrected,
#                                              2 = corrected, 3 = original
# Result:
#   pairs          [["a", "b"], ...]   (a, b) = a is a prerequisite of b
#   relation_form  "transitive_closure" (IITA selects quasi orders)
#   items, diff, error_rate, selection_set_index
#
# Direction was checked on simulated data: DAKS reports (a, b) when solving b
# implies solving a, which is the platform's convention, so nothing is flipped.
# DAKS refers to items by column index; they are mapped back to item ids here.

script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(script_dir, "common.R"))

run_analysis(packages = c("DAKS"), analysis = function(input) {
  frame <- response_frame(input$responses)
  version <- if (is.null(input$params$version)) 2L else as.integer(input$params$version)
  if (!version %in% 1:3) stop("params.version must be 1, 2 or 3.")

  fit <- iita(frame, v = version)

  items <- colnames(frame)
  pairs <- lapply(as.list(fit$implications), function(t) items[c(t[[1]], t[[2]])])

  list(
    items = items,
    pairs = pairs,
    relation_form = "transitive_closure",
    diff = fit$diff,
    error_rate = fit$error.rate,
    selection_set_index = fit$selection.set.index
  )
})
