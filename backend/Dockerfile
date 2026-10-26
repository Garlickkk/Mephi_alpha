FROM eclipse-temurin:21-jdk-jammy AS build
WORKDIR /workspace
ARG SERVICE
COPY ${SERVICE}/ .
RUN sh ./mvnw -B -DskipTests package
RUN cp target/*.jar /workspace/service.jar

FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
COPY --from=build /workspace/service.jar app.jar
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
