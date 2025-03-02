# AutoDS R Function Scraper
# This script expands the function database by:
# 1. Scraping a larger list of popular R packages
# 2. Extracting detailed function information
# 3. Storing the data in MongoDB
# 4. Testing scalability with larger package lists

library(rvest)
library(mongolite)
library(jsonlite)
library(parallel)

# Setup logging
log_message <- function(msg, level = "INFO") {
  timestamp <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  cat(sprintf("[%s] %s: %s\n", timestamp, level, msg))
}

# Connect to MongoDB with error handling
mongo_conn <- tryCatch({
  mongo(
    collection = "r_functions",
    db = "AutoDS",  # Consistent with Python script
    url = "mongodb://localhost:27017"
  )
}, error = function(e) {
  log_message(sprintf("Failed to connect to MongoDB: %s", e$message), "ERROR")
  stop("MongoDB connection failed. Please ensure MongoDB is running.")
})

# Function to get top CRAN packages
get_top_cran_packages <- function(limit = 150) {
  log_message("Fetching top CRAN packages")

  tryCatch({
    cran_url <- "https://cran.r-project.org/web/packages/available_packages_by_name.html"
    html_page <- read_html(cran_url)
    pkg_names <- html_page %>% html_nodes("td a") %>% html_text()
    top_packages <- head(pkg_names, limit)
    log_message(sprintf("Found %d packages to process", length(top_packages)))
    return(top_packages)
  }, error = function(e) {
    log_message(sprintf("Error fetching packages: %s", e$message), "ERROR")
    fallback_pkgs <- c(
      "ggplot2", "dplyr", "tidyr", "readr", "purrr", "tibble", "stringr",
      "forcats", "lubridate", "tidyverse", "data.table", "shiny",
      "rmarkdown", "knitr", "plotly", "rvest", "xml2", "httr",
      "jsonlite", "readxl", "openxlsx", "magrittr", "caret", "mlr",
      "randomForest", "xgboost", "glmnet", "lme4", "mgcv", "survival",
      "zoo", "forecast", "tseries", "prophet", "reshape2", "broom",
      "scales", "viridis", "RColorBrewer", "gganimate", "ggthemes",
      "leaflet", "sf", "raster", "sp", "rgdal", "maps", "mapdata"
    )
    return(fallback_pkgs)
  })
}

# Enhanced function to extract detailed information about R functions
get_package_functions <- function(pkg) {
  log_message(sprintf("Processing package: %s", pkg))

  tryCatch({
    if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
      install.packages(pkg, repos = "http://cran.us.r-project.org", quiet = TRUE)
      if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
        log_message(sprintf("Failed to install package: %s", pkg), "WARNING")
        return(NULL)
      }
    }

    exported_functions <- getNamespaceExports(pkg)
    log_message(sprintf("Found %d exported functions in %s", length(exported_functions), pkg))

    func_list <- list()
    for (func in exported_functions) {
      func_data <- tryCatch({
        f <- get(func, envir = asNamespace(pkg))
        if (!is.function(f)) return(NULL)

        args <- formals(f)
        arg_names <- names(args)
        defaults <- sapply(args, deparse, USE.NAMES = FALSE)

        body_text <- tryCatch(deparse(body(f)), error = function(e) "Unable to extract body")

        list(
          package = pkg,
          function_name = func,
          arguments = arg_names,
          default_values = defaults,
          full_function_call = paste0(pkg, "::", func, "(", paste(arg_names, collapse = ", "), ")"),
          body_preview = head(body_text, 10),
          body_length = length(body_text),
          description = tryCatch({
            help_text <- utils:::.getHelpFile(help(func, package = pkg))
            paste(utils:::.helpText(help_text), collapse = "\n")
          }, error = function(e) "No documentation available")
        )
      }, error = function(e) {
        log_message(sprintf("Error processing function %s::%s: %s", pkg, func, e$message), "DEBUG")
        NULL
      })

      if (!is.null(func_data)) func_list <- append(func_list, list(func_data))
    }

    log_message(sprintf("Successfully processed %d functions from %s", length(func_list), pkg))
    return(func_list)
  }, error = function(e) {
    log_message(sprintf("Failed to process package %s: %s", pkg, e$message), "ERROR")
    return(NULL)
  })
}

# Function to store package data in MongoDB
store_package_data <- function(pkg_data, pkg_name) {
  if (is.null(pkg_data) || length(pkg_data) == 0) {
    log_message(sprintf("No data to store for package %s", pkg_name), "WARNING")
    return(FALSE)
  }

  tryCatch({
    pkg_data_json <- toJSON(pkg_data, auto_unbox = TRUE)
    parsed_data <- fromJSON(pkg_data_json)
    mongo_conn$insert(parsed_data)
    log_message(sprintf("Successfully stored %d functions for %s in MongoDB", length(pkg_data), pkg_name))
    return(TRUE)
  }, error = function(e) {
    log_message(sprintf("Failed to store data for package %s: %s", e$message), "ERROR")
    return(FALSE)
  })
}

# Main function to orchestrate the entire process
main <- function() {
  log_message("Starting AutoDS R function database expansion")

  packages <- get_top_cran_packages(150)

  process_package <- function(pkg) {
    log_message(sprintf("Starting to process package: %s", pkg))
    start_time <- Sys.time()

    pkg_data <- get_package_functions(pkg)
    if (!is.null(pkg_data) && length(pkg_data) > 0) {
      success <- store_package_data(pkg_data, pkg)
    } else {
      success <- FALSE
    }

    end_time <- Sys.time()
    elapsed <- as.numeric(difftime(end_time, start_time, units = "secs"))

    log_message(sprintf("Finished processing %s in %.2f seconds. Success: %s",
                        pkg, elapsed, ifelse(success, "Yes", "No")))

    return(list(
      package = pkg,
      success = success,
      functions_count = if (!is.null(pkg_data)) length(pkg_data) else 0,
      processing_time = elapsed
    ))
  }

  log_message("Processing packages in parallel")
  num_cores <- min(detectCores() - 1, 4)
  batch_size <- 10
  num_batches <- ceiling(length(packages) / batch_size)

  results <- list()
  for (i in 1:num_batches) {
    batch_start <- (i - 1) * batch_size + 1
    batch_end <- min(i * batch_size, length(packages))
    batch_pkgs <- packages[batch_start:batch_end]

    log_message(sprintf("Processing batch %d/%d (%d packages)", i, num_batches, length(batch_pkgs)))
    batch_results <- mclapply(batch_pkgs, process_package, mc.cores = num_cores)
    results <- c(results, batch_results)
    Sys.sleep(5)
  }

  successful <- sum(sapply(results, function(x) x$success))
  total_functions <- sum(sapply(results, function(x) x$functions_count))
  total_time <- sum(sapply(results, function(x) x$processing_time))

  log_message(sprintf("Database expansion completed:"))
  log_message(sprintf("  - Processed %d packages", length(packages)))
  log_message(sprintf("  - Successfully processed %d packages", successful))
  log_message(sprintf("  - Stored %d functions in MongoDB", total_functions))
  log_message(sprintf("  - Total processing time: %.2f seconds", total_time))

  summary_data <- list(
    timestamp = as.character(Sys.time()),
    packages_processed = length(packages),
    packages_successful = successful,
    total_functions = total_functions,
    total_processing_time = total_time
  )

  write(toJSON(summary_data, auto_unbox = TRUE), "r_processing_summary.json")
  log_message("Summary exported to r_processing_summary.json")

  mongo_conn$disconnect()
  log_message("MongoDB connection closed")
}

# Run the main function
if (!interactive()) main()