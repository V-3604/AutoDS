#!/usr/bin/env Rscript

# AutoDS R Function Scraper
# This script expands the function database by:
# 1. Scraping essential R packages needed for AutoDS
# 2. Extracting detailed function information from each package
# 3. Storing the data in MongoDB

# ---- Check and Install Required Packages ----
required_packages <- c("jsonlite", "mongolite")
for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cran.r-project.org")
  }
}

# ---- Load Required Libraries ----
library(jsonlite)
library(mongolite)

# Set a longer download timeout
options(timeout = 300)

# Set up custom directories
custom_dir_base <- "/Users/varshithgowdak/Desktop/AutoDS"
custom_lib_dir <- file.path(custom_dir_base, "R_packages")
dir.create(custom_lib_dir, showWarnings = FALSE, recursive = TRUE)

# Setup logging
log_file <- file.path(custom_dir_base, "autods_log.txt")
log_message <- function(msg, level = "INFO") {
  timestamp <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  log_entry <- sprintf("[%s] %s: %s\n", timestamp, level, msg)
  cat(log_entry)
  cat(log_entry, file = log_file, append = TRUE)
}

log_message("Starting AutoDS R function scraper")

# Connect to MongoDB
mongo_conn <- tryCatch({
  mongo(
    collection = "r_functions",
    db = "AutoDS",
    url = "mongodb://localhost:27017"
  )
}, error = function(e) {
  log_message(sprintf("Failed to connect to MongoDB: %s", e$message), "ERROR")
  stop("MongoDB connection failed. Please ensure MongoDB is running.")
})

# Define essential packages for AutoDS
core_packages <- c(
  # Essential statistics and modeling packages
  "stats",
  "rpart",       # Decision trees
  "randomForest", # Random forests
  "e1071",       # SVM, Naive Bayes
  "cluster",     # Clustering algorithms
  "glmnet",      # Regularized regression
  "MASS"         # Statistical functions
)

log_message(sprintf("Will process %d essential packages", length(core_packages)))

# Clear existing data
tryCatch({
  count_before <- mongo_conn$count()
  if (count_before > 0) {
    log_message(sprintf("Clearing %d existing records from MongoDB", count_before))
    mongo_conn$drop()
  }
}, error = function(e) {
  log_message(sprintf("Error checking/clearing MongoDB: %s", e$message), "WARNING")
})

# Function to get package details
get_package_functions <- function(pkg) {
  log_message(sprintf("Processing package: %s", pkg))

  tryCatch({
    # Install package if needed
    if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
      log_message(sprintf("Installing package %s", pkg))
      install.packages(pkg, repos = "https://cran.r-project.org", quiet = TRUE)

      if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
        log_message(sprintf("Failed to install package: %s", pkg), "ERROR")
        return(NULL)
      }
    }

    # Get exported functions
    exported_functions <- tryCatch({
      getNamespaceExports(pkg)
    }, error = function(e) {
      log_message(sprintf("Error getting exports from %s: %s", pkg, e$message), "ERROR")
      character(0)
    })

    if (length(exported_functions) == 0) {
      log_message(sprintf("No exported functions found in %s", pkg), "WARNING")
      return(NULL)
    }

    log_message(sprintf("Found %d exported functions in %s", length(exported_functions), pkg))

    # Process each function
    func_list <- list()
    for (func in exported_functions) {
      func_data <- tryCatch({
        # Skip functions with special characters
        if (grepl("[<>$@:^&*(){}\\[\\]|]", func)) {
          return(NULL)
        }

        # Get function object
        f <- tryCatch(get(func, envir = asNamespace(pkg)), error = function(e) NULL)
        if (is.null(f) || !is.function(f)) return(NULL)

        # Get arguments
        args <- formals(f)
        arg_names <- names(args)

        # Process default values safely
        defaults <- lapply(args, function(x) {
          tryCatch({
            if (is.language(x) || is.call(x)) {
              deparse(x)
            } else if (is.null(x)) {
              "NULL"
            } else {
              as.character(x)
            }
          }, error = function(e) "")
        })

        # Format arguments for MongoDB
        arg_list <- lapply(seq_along(arg_names), function(i) {
          list(
            name = arg_names[i],
            default = as.character(defaults[[i]])
          )
        })

        # Get documentation
        help_text <- tryCatch({
          help_obj <- help(func, package = pkg)
          if (length(help_obj) > 0) {
            help_file <- utils:::.getHelpFile(help_obj)
            paste(utils:::.helpText(help_file), collapse = "\n")
          } else {
            "No documentation available"
          }
        }, error = function(e) {
          "No documentation available"
        })

        # Create a simplified description from the first paragraph of help
        description <- tryCatch({
          first_para <- strsplit(help_text, "\n\n")[[1]][1]
          if (is.null(first_para) || first_para == "") {
            sprintf("Function %s::%s", pkg, func)
          } else {
            first_para
          }
        }, error = function(e) {
          sprintf("Function %s::%s", pkg, func)
        })

        # Create the function data object
        list(
          package = pkg,
          function_name = func,
          arguments = arg_list,
          full_function_call = sprintf("%s::%s(%s)", pkg, func, paste(arg_names, collapse = ", ")),
          description = description,
          docstring = help_text,
          language = "r"
        )
      }, error = function(e) {
        log_message(sprintf("Error processing function %s::%s: %s", pkg, func, e$message), "DEBUG")
        NULL
      })

      if (!is.null(func_data)) {
        func_list <- append(func_list, list(func_data))
      }
    }

    log_message(sprintf("Successfully processed %d functions from %s", length(func_list), pkg))
    return(func_list)
  }, error = function(e) {
    log_message(sprintf("Failed to process package %s: %s", pkg, e$message), "ERROR")
    return(NULL)
  })
}

# Store functions in MongoDB
store_package_data <- function(pkg_data, pkg) {
  if (is.null(pkg_data) || length(pkg_data) == 0) {
    log_message(sprintf("No data to store for package %s", pkg), "WARNING")
    return(FALSE)
  }

  tryCatch({
    # Insert each function individually to avoid JSON conversion issues
    inserted_count <- 0

    for (func_data in pkg_data) {
      tryCatch({
        # Convert to JSON then back to ensure MongoDB compatibility
        func_json <- toJSON(func_data, auto_unbox = TRUE, null = "null")
        func_parsed <- fromJSON(func_json)

        # Insert the function
        mongo_conn$insert(func_parsed)
        inserted_count <- inserted_count + 1
      }, error = function(e) {
        log_message(sprintf("Error storing function %s: %s",
                          func_data$function_name, e$message), "WARNING")
      })
    }

    log_message(sprintf("Successfully stored %d/%d functions for %s in MongoDB",
                      inserted_count, length(pkg_data), pkg))
    return(inserted_count > 0)
  }, error = function(e) {
    log_message(sprintf("Failed to store data for package %s: %s", pkg, e$message), "ERROR")
    return(FALSE)
  })
}

# Main processing function
process_all_packages <- function() {
  log_message("Starting to process packages")
  total_start_time <- Sys.time()

  successful_packages <- 0
  total_functions <- 0

  for (pkg in core_packages) {
    log_message(sprintf("Processing package %d/%d: %s",
                      which(core_packages == pkg), length(core_packages), pkg))

    start_time <- Sys.time()

    # Get functions
    pkg_functions <- get_package_functions(pkg)

    # Store functions
    success <- FALSE
    functions_count <- 0

    if (!is.null(pkg_functions) && length(pkg_functions) > 0) {
      success <- store_package_data(pkg_functions, pkg)
      functions_count <- length(pkg_functions)

      if (success) {
        successful_packages <- successful_packages + 1
        total_functions <- total_functions + functions_count
      }
    }

    end_time <- Sys.time()
    elapsed <- as.numeric(difftime(end_time, start_time, units = "secs"))

    log_message(sprintf("Finished processing %s in %.2f seconds. Success: %s, Functions: %d",
                      pkg, elapsed, ifelse(success, "Yes", "No"), functions_count))
  }

  total_end_time <- Sys.time()
  total_time <- as.numeric(difftime(total_end_time, total_start_time, units = "secs"))

  log_message("Database expansion completed:")
  log_message(sprintf("  - Processed %d packages", length(core_packages)))
  log_message(sprintf("  - Successfully processed %d packages", successful_packages))
  log_message(sprintf("  - Stored %d functions in MongoDB", total_functions))
  log_message(sprintf("  - Total processing time: %.2f seconds", total_time))

  # Save summary
  summary_data <- list(
    timestamp = as.character(Sys.time()),
    packages_processed = length(core_packages),
    packages_successful = successful_packages,
    total_functions = total_functions,
    total_processing_time = total_time
  )

  summary_file <- file.path(custom_dir_base, "r_processing_summary.json")
  write(toJSON(summary_data, auto_unbox = TRUE), summary_file)
  log_message(sprintf("Summary exported to %s", summary_file))
}

# Run the main function
tryCatch({
  process_all_packages()
  mongo_conn$disconnect()
  log_message("MongoDB connection closed")
}, error = function(e) {
  log_message(sprintf("Critical error in processing: %s", e$message), "ERROR")
  if (exists("mongo_conn")) {
    mongo_conn$disconnect()
  }
})

log_message("R function scraper completed")