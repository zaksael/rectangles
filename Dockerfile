# syntax=docker/dockerfile:1

FROM node:24-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM eclipse-temurin:25-jdk AS server
ADD --checksum=sha256:783fe0c278564e67fbd14ecaa9ace6b9433cf8ece0ad8f50ad436cb24622105c https://github.com/sbt/sbt/releases/download/v2.0.10/sbt-2.0.10.tgz /tmp/sbt.tgz
RUN tar -xzf /tmp/sbt.tgz -C /opt && rm /tmp/sbt.tgz
ENV PATH=/opt/sbt/bin:$PATH
WORKDIR /app/server-scala
# Resolve the dependencies in their own layer, so a source change does not download them again.
COPY server-scala/project project
COPY server-scala/build.sbt ./
RUN sbt -batch update
COPY server-scala/ ./
RUN sbt -batch server/stage

FROM eclipse-temurin:25-jre
RUN useradd --system --uid 10001 rectangles
WORKDIR /app
COPY --from=server /app/server-scala/target/stage/ ./
COPY --from=frontend /app/frontend/dist ./frontend/dist
ENV RECTANGLES_SERVER_HOST=0.0.0.0 \
    LOGGING4S_CONSOLE_FORMAT=json
EXPOSE 8765
USER rectangles
# the JRE image has no curl; bash can open the socket itself
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD bash -c 'exec 3<>/dev/tcp/127.0.0.1/${RECTANGLES_SERVER_PORT:-8765} && printf "GET /health HTTP/1.0\r\n\r\n" >&3 && grep -qx ok <&3' || exit 1
ENTRYPOINT ["/app/bin/rectangles-server"]
