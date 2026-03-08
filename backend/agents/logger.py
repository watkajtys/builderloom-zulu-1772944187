import logging
import json
import datetime
import traceback

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the LogRecord.
    """
    def __init__(self, fmt_dict: dict = None, datefmt: str = "%Y-%m-%dT%H:%M:%SZ"):
        self.fmt_dict = fmt_dict if fmt_dict is not None else {
            "timestamp": "asctime",
            "level": "levelname",
            "agent": "agent",
            "event_type": "event_type",
            "message": "message",
            "context": "context"
        }
        self.datefmt = datefmt
        super().__init__(fmt=None, datefmt=datefmt)

    def usesTime(self) -> bool:
        return "asctime" in self.fmt_dict.values()

    def formatMessage(self, record) -> dict:
        message_dict = {}
        for fmt_key, fmt_val in self.fmt_dict.items():
            if fmt_val == "message":
                message_dict[fmt_key] = record.getMessage()
            elif fmt_val == "asctime":
                message_dict[fmt_key] = self.formatTime(record, self.datefmt)
            elif hasattr(record, fmt_val):
                message_dict[fmt_key] = getattr(record, fmt_val)
            else:
                # If the attribute isn't found (e.g., standard loggers missing custom attributes)
                # provide a default to keep the JSON schema valid
                if fmt_key == "agent":
                    message_dict[fmt_key] = "system"
                elif fmt_key == "event_type":
                    message_dict[fmt_key] = "unknown"
                elif fmt_key == "context":
                    message_dict[fmt_key] = {}
                else:
                    message_dict[fmt_key] = None
        return message_dict

    def format(self, record: logging.LogRecord) -> str:
        # Default agent and event_type for generic logs
        if not hasattr(record, 'agent'):
            record.agent = 'system'
        if not hasattr(record, 'event_type'):
            # simple heuristic, if it's an error level it's an error, otherwise action/thought based on caller context
            record.event_type = 'error' if record.levelno >= logging.ERROR else 'action'
        if not hasattr(record, 'context'):
            record.context = {}

        message_dict = self.formatMessage(record)

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            message_dict["exc_info"] = record.exc_text

        if record.stack_info:
            message_dict["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(message_dict, default=str)


def get_logger(name: str, agent_id: str = "system") -> logging.Logger:
    """
    Returns a configured logger instance that emits JSON formatted logs.
    """
    logger = logging.getLogger(name)
    
    # Store agent_id in a way that we can use it to inject into LogRecords
    # To do this without a custom Logger class (which can conflict if getLogger is called multiple times),
    # we can use a LoggerAdapter to inject kwargs into every log call
    
    # Prevent adding multiple handlers if logger is requested multiple times
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        # Prevent propagation to root logger to avoid duplicate logs if root has handlers
        logger.propagate = False
        
    return logger

class AgentLogger(logging.LoggerAdapter):
    """
    A LoggerAdapter that injects agent, event_type, and context into log records.
    """
    def __init__(self, logger: logging.Logger, agent_id: str):
        super().__init__(logger, {})
        self.agent_id = agent_id

    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        
        # Extract custom fields from kwargs if present
        event_type = kwargs.pop("event_type", "action")
        context = kwargs.pop("context", {})
        
        extra["agent"] = self.agent_id
        extra["event_type"] = event_type
        extra["context"] = context
        
        kwargs["extra"] = extra
        return msg, kwargs
        
    def thought(self, msg, context=None, *args, **kwargs):
        if context is None: context = {}
        kwargs["event_type"] = "thought"
        kwargs["context"] = context
        self.info(msg, *args, **kwargs)

    def action(self, msg, context=None, *args, **kwargs):
        if context is None: context = {}
        kwargs["event_type"] = "action"
        kwargs["context"] = context
        self.info(msg, *args, **kwargs)

    def error_event(self, msg, context=None, *args, **kwargs):
        if context is None: context = {}
        kwargs["event_type"] = "error"
        kwargs["context"] = context
        self.error(msg, *args, **kwargs)

def get_agent_logger(name: str, agent_id: str) -> AgentLogger:
    """
    Returns an AgentLogger instance wrapped around a JSON-configured logger.
    """
    base_logger = get_logger(name)
    return AgentLogger(base_logger, agent_id)

