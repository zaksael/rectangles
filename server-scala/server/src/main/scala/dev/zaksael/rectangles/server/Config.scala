package dev.zaksael.rectangles.server

import cats.effect.IO
import com.comcast.ip4s.Host
import com.comcast.ip4s.Port
import pureconfig.ConfigReader
import pureconfig.ConfigReader.Result
import pureconfig.ConfigSource
import pureconfig.error.CannotConvert
import pureconfig.error.ConfigReaderException

final case class Config(host: Host, port: Port) derives ConfigReader

object Config:
  given ConfigReader[Host] = ConfigReader.fromNonEmptyString(s =>
    Host.fromString(s).toRight(CannotConvert(s, "Host", "not a valid host"))
  )
  given ConfigReader[Port] = ConfigReader[Int].emap(i =>
    Port.fromInt(i).toRight(CannotConvert(i.toString, "Port", "must be 0 to 65535"))
  )

  /** The `server` section of a config source. */
  def from(source: ConfigSource): Result[Config] = source.at("server").load[Config]

  /** `application.conf`, with `RECTANGLES_SERVER_HOST` and `_PORT` overriding the defaults. */
  val load: IO[Config] =
    IO.fromEither(from(ConfigSource.default).left.map(ConfigReaderException[Config](_)))
