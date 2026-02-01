# Additional clean files
cmake_minimum_required(VERSION 3.16)

if("${CONFIG}" STREQUAL "" OR "${CONFIG}" STREQUAL "Debug")
  file(REMOVE_RECURSE
  "AVDownloader_autogen"
  "CMakeFiles\\AVDownloader_autogen.dir\\AutogenUsed.txt"
  "CMakeFiles\\AVDownloader_autogen.dir\\ParseCache.txt"
  )
endif()
