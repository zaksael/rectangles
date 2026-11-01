package dev.zaksael.rectangles.server.http

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class OriginCheckSpec extends AnyFlatSpec with Matchers:
  "a page from the same host and port" should "be allowed" in {
    OriginCheck.allowed(Some("http://testserver"), Some("testserver")) shouldBe true
    OriginCheck.allowed(Some("http://localhost:5173"), Some("localhost:5173")) shouldBe true
  }

  "a host written in another letter case" should "still match the page's origin" in {
    OriginCheck.allowed(Some("http://example.com"), Some("Example.COM")) shouldBe true
    OriginCheck.allowed(Some("http://Example.COM:8080"), Some("example.com:8080")) shouldBe true
  }

  "an IPv6 host" should "match its own port and no other" in {
    OriginCheck.allowed(Some("http://[::1]:8765"), Some("[::1]:8765")) shouldBe true
    OriginCheck.allowed(Some("http://[::1]:9999"), Some("[::1]:8765")) shouldBe false
  }

  "a page from anywhere else" should "be refused" in {
    for origin <- Seq("http://evil.example", "http://testserver:9999", "null", "not a url") do
      withClue(origin)(OriginCheck.allowed(Some(origin), Some("testserver")) shouldBe false)
  }

  "a client that sends no Origin" should "be allowed, since only browsers can be hijacked from another site" in {
    OriginCheck.allowed(None, Some("testserver")) shouldBe true
  }

  "a page whose origin has no host" should "be refused even when no Host header came with it" in {
    OriginCheck.allowed(Some("null"), None) shouldBe false
  }
