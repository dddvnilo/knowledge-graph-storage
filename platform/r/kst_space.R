# Knowledge space spanned by a prerequisite relation (kst::kspace).
#
# Input:
#   relation  {"items": [...], "pairs": [["a", "b"], ...], "relation_form": ...}
#             (a, b) = a is a prerequisite of b
# Result:
#   items   item ids, in the same order as the input
#   states  [[0, 1, ...], ...]  one row per knowledge state, columns in item order
#
# kst needs a reflexive and transitively closed relation, otherwise it silently
# returns wrong states. Both are added here, whatever the input's relation_form.
# Isolated items stay in the domain because every item gets its reflexive pair.

script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(script_dir, "common.R"))

run_analysis(packages = c("kst", "sets", "relations"), analysis = function(input) {
  items <- input$relation$items
  m <- transitive_closure(relation_matrix(input$relation))
  diag(m) <- 1L

  space <- kspace(kstructure(as.relation(m)))
  states <- unclass(as.binaryMatrix(space))[, items, drop = FALSE]
  states <- states[do.call(order, c(list(rowSums(states)), as.data.frame(-states))), , drop = FALSE]

  list(items = items, states = unname(states))
})
