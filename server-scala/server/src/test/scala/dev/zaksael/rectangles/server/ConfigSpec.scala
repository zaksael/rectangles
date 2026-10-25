package dev.zaksael.rectangles.server

import java.nio.file.Path

import com.comcast.ip4s.ipv4
import com.comcast.ip4s.port
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import pureconfig.ConfigSource

class ConfigSpec extends AnyFlatSpec with Matchers:
  "Config" should "default to 127.0.0.1 on port 8765, serving frontend/dist" in {
    Config.from(ConfigSource.default) shouldBe
      Right(Config(ipv4"127.0.0.1", port"8765", Path.of("frontend/dist")))
  }

  it should "read a host, port and frontend folder from its source" in {
    val source = ConfigSource.string(
      "server { host = \"0.0.0.0\", port = 9000, frontend-dist = \"/srv/web\" }"
    )
    Config.from(source) shouldBe Right(Config(ipv4"0.0.0.0", port"9000", Path.of("/srv/web")))
  }

  it should "reject a port out of range" in {
    Config.from(
      ConfigSource.string("server { host = \"x\", port = 70000, frontend-dist = \"d\" }")
    ).isLeft shouldBe true
  }
