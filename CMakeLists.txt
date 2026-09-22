# CoopAgent (documentation-agent) — Python 프로젝트를 위한 CMake 빌드 오케스트레이터
#
# 역할:
#   - CTest : pytest 단위 테스트(test/) 실행
#   - CPack : Python 패키지를 ZIP / TGZ 아카이브로 패키징
#
# 사용법:
#   cmake -S . -B build
#   cmake --build build
#   ctest --test-dir build --output-on-failure
#   cmake --build build --target package   # 또는: cpack --config build/CPackConfig.cmake

cmake_minimum_required(VERSION 3.20)

project(documentation-agent VERSION 0.2.1 LANGUAGES NONE)

# --- Python 인터프리터 (pytest 실행용) ---
# 활성화된 가상환경(.venv)이 있으면 그 인터프리터를 우선 사용한다.
if(DEFINED ENV{VIRTUAL_ENV})
    if(WIN32)
        set(_venv_python "$ENV{VIRTUAL_ENV}/Scripts/python.exe")
    else()
        set(_venv_python "$ENV{VIRTUAL_ENV}/bin/python")
    endif()
    if(EXISTS "${_venv_python}")
        set(Python_EXECUTABLE "${_venv_python}" CACHE FILEPATH "Python interpreter from active venv")
    endif()
endif()

find_package(Python 3.11 REQUIRED COMPONENTS Interpreter)

# --- CTest ---
enable_testing()

# pytest는 소스 루트에서 실행하여 pyproject.toml의 설정을 사용한다.
# ([tool.pytest.ini_options] 에서 testpaths=test, pythonpath=src 를 지정)
add_test(
    NAME pytest
    COMMAND ${Python_EXECUTABLE} -m pytest
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
)

# --- Install 규칙 (CPack이 소비) ---
set(SITE_PACKAGES "lib/python${Python_VERSION_MAJOR}.${Python_VERSION_MINOR}/site-packages")
install(DIRECTORY src/documentation_agent
        DESTINATION ${SITE_PACKAGES}
        PATTERN "__pycache__" EXCLUDE)
install(DIRECTORY src/agents
        DESTINATION ${SITE_PACKAGES}
        PATTERN "__pycache__" EXCLUDE)
install(DIRECTORY src/rag
        DESTINATION ${SITE_PACKAGES}
        PATTERN "__pycache__" EXCLUDE)
install(FILES pyproject.toml requirements.txt
        DESTINATION share/documentation-agent)

# --- CPack ---
set(CPACK_PACKAGE_NAME "documentation-agent")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_VENDOR "YoungGee Kim")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Persona-based interview to requirements/workflow spec agent")
set(CPACK_PACKAGE_HOMEPAGE_URL "https://github.com/populous/coopagent")
set(CPACK_GENERATOR "ZIP;TGZ")
include(CPack)
