package dev.zaksael.rectangles.server.protocol

/** `wire` is the name clients receive in an `error` message. */
enum ErrorReason(val wire: String):
  case InvalidAction           extends ErrorReason("invalidAction")
  case IllegalPlacement        extends ErrorReason("illegalPlacement")
  case ProtocolVersionMismatch extends ErrorReason("protocolVersionMismatch")
  case IllegalWildcardValue    extends ErrorReason("illegalWildcardValue")
  case MalformedMessage        extends ErrorReason("malformedMessage")
