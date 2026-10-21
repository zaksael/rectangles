package dev.zaksael.rectangles.server

import io.circe.Json

object JsonDiff:
  /**
   * Arrays under these keys are compared without regard to order (Python builds them from sets).
   */
  private val unordered = Set("topLefts")

  def diff(expected: Json, actual: Json, path: String = "$", key: String = ""): List[String] =
    (expected.asObject, actual.asObject, expected.asArray, actual.asArray) match
      case (Some(want), Some(got), _, _) =>
        val keys = (want.keys ++ got.keys).toList.distinct
        keys.flatMap { name =>
          (want(name), got(name)) match
            case (Some(w), Some(g)) => diff(w, g, s"$path.$name", name)
            case (Some(_), None)    => List(s"$path.$name: missing")
            case (None, _)          => List(s"$path.$name: unexpected")
        }
      case (_, _, Some(want), Some(got)) if unordered(key) =>
        if want.toSet == got.toSet then Nil
        else List(s"$path: expected ${expected.noSpaces}, got ${actual.noSpaces}")
      case (_, _, Some(want), Some(got)) =>
        if want.size != got.size then List(s"$path: expected ${want.size} items, got ${got.size}")
        else
          want.zip(got).zipWithIndex.flatMap { case ((w, g), i) =>
            diff(w, g, s"$path[$i]", key)
          }.toList
      case _ =>
        if expected == actual then Nil
        else List(s"$path: expected ${expected.noSpaces}, got ${actual.noSpaces}")
