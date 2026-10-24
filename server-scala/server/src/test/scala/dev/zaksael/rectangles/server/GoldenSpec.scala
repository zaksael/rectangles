package dev.zaksael.rectangles.server

import java.nio.file.Files

import scala.jdk.CollectionConverters.*

import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class GoldenSpec extends AnyFlatSpec with Matchers with EitherValues:
  "the golden vanilla set" should "load with its connect, draws and steps" in {
    val game = Golden.load("vanilla").value
    game.name shouldBe "vanilla"
    game.connect shouldBe Map("protocolVersion" -> "1", "boardSize" -> "19")
    game.pinnedStarter shouldBe true
    game.draws.size shouldBe 24
    game.draws.head should matchPattern { case Draw.RandInt(1, 6, _) => }
    game.steps.size shouldBe 26
    game.steps.head.send shouldBe None
    game.steps.head.receive.size shouldBe 1
  }

  it should "sit beside every other set, and all of them load" in {
    val names = Files.list(Golden.dir).iterator().asScala.map(_.getFileName.toString).toList
    names.size shouldBe 16
    names.foreach(file => Golden.load(file.stripSuffix(".json")).isRight shouldBe true)
  }

  "Golden.update" should "rewrite a fixture only when the update mode is on" in {
    val tmp = Files.createTempDirectory("golden")
    Golden.update("x", "one", tmp, enabled = false) shouldBe false
    Files.exists(tmp.resolve("x.json")) shouldBe false
    Golden.update("x", "one", tmp, enabled = true) shouldBe true
    Files.readString(tmp.resolve("x.json")) shouldBe "one"
  }
