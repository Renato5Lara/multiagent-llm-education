# Sandbox de C++ para AG2: compila (g++ -std=c++17 -Wall -Wextra) y ejecuta el código generado + sus pruebas.
# Se ejecuta SIEMPRE sin red, con memoria/PIDs limitados y raíz de solo lectura (ver adaptation_swarm/sandbox_cpp.py).
FROM docker.io/library/alpine:3.20
RUN apk add --no-cache g++ musl-dev
WORKDIR /work
