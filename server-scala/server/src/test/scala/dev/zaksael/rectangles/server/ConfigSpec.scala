package dev.zaksael.rectangles.server

import com.comcast.ip4s.ipv4
import com.comcast.ip4s.port
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import pureconfig.ConfigSource

class ConfigSpec extends AnyFlatSpec with Matchers:
  "Config" should "default to 127.0.0.1 on port 8765" in {
    Config.from(ConfigSource.default) shouldBe Right(Config(ipv4"127.0.0.1", port"8765"))
  }

  it should "read a host and port from its source" in {
    val source = ConfigSource.string("server { host = \"0.0.0.0\", port = 9000 }")
    Config.from(source) shouldBe Right(Config(ipv4"0.0.0.0", port"9000"))
  }

  it should "reject a port out of range" in {
    Config.from(ConfigSource.string("server { host = \"x\", port = 70000 }")).isLeft shouldBe true
  }
