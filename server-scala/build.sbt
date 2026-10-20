ThisBuild / organization := "dev.zaksael"
ThisBuild / scalaVersion := "3.8.3"
ThisBuild / version := "0.1.0"

val scalatest = "org.scalatest" %% "scalatest" % "3.2.19" % Test

lazy val core = project
  .in(file("core"))
  .settings(name := "rectangles-core", libraryDependencies += scalatest)

lazy val server = project
  .in(file("server"))
  .dependsOn(core)
  .settings(name := "rectangles-server", libraryDependencies += scalatest)

lazy val root = project
  .in(file("."))
  .aggregate(core, server)
  .settings(name := "rectangles", publish / skip := true)
