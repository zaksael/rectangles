ThisBuild / organization := "dev.zaksael"
ThisBuild / scalaVersion := "3.9.0"
ThisBuild / version := "0.1.0"

ThisBuild / scalacOptions ++= Seq(
  "-Werror",
  "-deprecation",
  "-feature",
  "-unchecked",
  "-Wunused:all",
  "-Wvalue-discard"
)
ThisBuild / semanticdbEnabled := true

val strict = Seq(
  wartremoverErrors ++= Seq(Wart.Var, Wart.Null, Wart.Throw)
)

val scalatest = "org.scalatest" %% "scalatest" % "3.2.19" % Test

lazy val core = project
  .in(file("core"))
  .settings(strict, name := "rectangles-core", libraryDependencies += scalatest)

lazy val server = project
  .in(file("server"))
  .dependsOn(core)
  .settings(
    strict,
    name := "rectangles-server",
    libraryDependencies ++= Seq(
      "org.http4s" %% "http4s-ember-server" % "0.23.38",
      "org.http4s" %% "http4s-dsl" % "0.23.38",
      "io.circe" %% "circe-core" % "0.14.17",
      "com.github.pureconfig" %% "pureconfig-core" % "0.17.11",
      "org.logging4s" %% "logging4s-cats" % "5.0.0",
      "org.logging4s" %% "logging4s-console" % "5.0.0",
      "org.slf4j" % "slf4j-simple" % "2.0.17" % Runtime,
      scalatest
    )
  )

lazy val root = project
  .in(file("."))
  .aggregate(core, server)
  .settings(name := "rectangles", publish / skip := true)
