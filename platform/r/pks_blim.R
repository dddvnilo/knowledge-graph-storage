# Basic local independence model (pks::blim).
#
# Input:
#   structure  {"items": [...], "states": [[0, 1, ...], ...]}
#   responses  {"items": [...], "matrix": [[0, 1, ...], ...]}  same items, any order
#   params     {"method": "ML" | "MD" | "MDML"}
# Result:
#   items, method
#   beta, eta            per item: probability of a careless error / lucky guess
#   state_probabilities  one per state, in the order of the input states
#   loglik, npar, aic, bic, g2, df, p_value, discrepancy, n_respondents
#
# pks matches the columns of K and of the response patterns by position, not
# by name: with the wrong order it returns a meaningless fit without an error.
# Both are therefore put in the structure's item order here.

script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(script_dir, "common.R"))

run_analysis(packages = c("pks"), analysis = function(input) {
  items <- input$structure$items
  method <- if (is.null(input$params$method)) "ML" else input$params$method
  if (!method %in% c("ML", "MD", "MDML")) stop("params.method must be ML, MD or MDML.")

  K <- structure_matrix(input$structure)
  patterns <- aligned_responses(input$responses, items)
  N.R <- as.pattern(patterns, freq = TRUE)

  fit <- blim(K, N.R, method = method)
  gof <- fit$goodness.of.fit

  list(
    items = items,
    method = method,
    beta = as.list(setNames(unname(fit$beta), items)),
    eta = as.list(setNames(unname(fit$eta), items)),
    state_probabilities = unname(fit$P.K),
    loglik = as.numeric(logLik(fit)),
    npar = fit$npar,
    aic = AIC(fit),
    bic = BIC(fit),
    g2 = unname(gof["G2"]),
    df = unname(gof["df"]),
    p_value = unname(gof["pval"]),
    discrepancy = fit$discrepancy,
    n_respondents = fit$ntotal
  )
})
