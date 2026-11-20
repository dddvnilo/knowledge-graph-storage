# Shared helpers for analysis scripts.
#
# Every analysis script is called the same way:
#   Rscript <script>.R <input.json> <output.json>
# It reads its input from the JSON file and always writes a JSON envelope:
#   {"status": "ok" | "error", "result": ..., "error": ..., "environment": ...}
# The Python side never parses R console output; it only reads this envelope.

suppressPackageStartupMessages(library(jsonlite))

environment_info <- function(packages) {
  versions <- lapply(packages, function(p) as.character(packageVersion(p)))
  names(versions) <- packages
  list(
    r_version = paste(R.version$major, R.version$minor, sep = "."),
    packages = versions
  )
}

# Runs `analysis(input)` and writes the envelope. `packages` are the R packages
# whose versions belong to the provenance of the result.
run_analysis <- function(analysis, packages) {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) != 2) stop("Usage: Rscript <script>.R <input.json> <output.json>")
  output_path <- args[2]

  envelope <- tryCatch({
    input <- fromJSON(args[1], simplifyVector = TRUE)
    for (p in packages) suppressPackageStartupMessages(library(p, character.only = TRUE))
    list(status = "ok", result = analysis(input), environment = environment_info(packages))
  }, error = function(e) {
    list(status = "error", error = conditionMessage(e))
  })

  write_json(envelope, output_path, auto_unbox = TRUE, digits = NA, null = "null")
}

# Converts a "responses" input ({items, matrix}) into a data frame
# whose columns are named after the items.
response_frame <- function(x) {
  items <- x$items
  responses <- x$matrix
  if (!is.matrix(responses)) responses <- matrix(responses, ncol = length(items))
  if (ncol(responses) != length(items)) stop("Number of columns does not match number of items.")
  if (!all(responses %in% c(0, 1))) stop("Responses must contain only 0 and 1.")
  frame <- as.data.frame(responses)
  colnames(frame) <- items
  frame
}

# Converts a "prerequisite_relation" input ({items, pairs}) into an
# items x items 0/1 matrix: M[a, b] = 1 means a is a prerequisite of b.
relation_matrix <- function(x) {
  items <- x$items
  m <- matrix(0L, length(items), length(items), dimnames = list(items, items))
  pairs <- x$pairs
  if (length(pairs) == 0) return(m)
  if (!is.matrix(pairs)) pairs <- matrix(unlist(pairs), ncol = 2, byrow = TRUE)
  if (!all(pairs %in% items)) stop("Pairs refer to items that are not in the item list.")
  m[pairs] <- 1L
  m
}

# Transitive closure (Warshall), without reflexive pairs.
transitive_closure <- function(m) {
  for (k in seq_len(nrow(m))) m <- (m | outer(m[, k], m[k, ], "&")) * 1L
  diag(m) <- 0L
  m
}
