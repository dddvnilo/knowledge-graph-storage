# Fit of a knowledge structure to response data (kst::kvalidate).
#
# Input:
#   structure  {"items": [...], "states": [[0, 1, ...], ...]}
#   responses  {"items": [...], "matrix": [[0, 1, ...], ...]}  same items, any order
# Result:
#   gamma, concordant, discordant   gamma index of the structure's prerequisite
#                                   relation: from -1 to 1, higher supports it
#   vc                              violational coefficient: share of violations,
#                                   lower is better
#   di, di_distribution             discrepancy index: mean distance from each
#                                   response pattern to the closest state, lower
#                                   is better; distribution {distance: count}
#   da, ddat, dpot                  distance agreement: di relative to the mean
#                                   distance to the power set, lower is better
#
# kvalidate accepts only a structure (not a relation); gamma and VC are
# computed on the surmise relation the structure implies.

script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(script_dir, "common.R"))

as_distribution <- function(table) as.list(setNames(as.integer(table), names(table)))

run_analysis(packages = c("kst", "sets", "relations"), analysis = function(input) {
  items <- input$structure$items
  structure <- kst_structure(input$structure)
  patterns <- aligned_responses(input$responses, items)

  gamma <- kvalidate(structure, rpatterns = patterns, method = "gamma")
  vc <- kvalidate(structure, rpatterns = patterns, method = "VC")
  di <- kvalidate(structure, rpatterns = patterns, method = "DI")
  da <- kvalidate(structure, rpatterns = patterns, method = "DA")

  list(
    items = items,
    n_respondents = nrow(patterns),
    gamma = gamma$gamma,
    concordant = gamma$nc,
    discordant = gamma$nd,
    vc = vc$vc,
    di = di$di,
    di_distribution = as_distribution(di$di_dist),
    da = da$DA,
    ddat = da$ddat,
    dpot = da$dpot
  )
})
