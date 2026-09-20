import re
from dataclasses import asdict, dataclass, field


@dataclass
class ParsedQuestion:
    text: str
    options: list[str]
    correct_index: int
    explanation: str = ""
    start_line: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass
class ParseError:
    line: int
    message: str


@dataclass
class ParseResult:
    questions: list[ParsedQuestion] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)


PREFIX = re.compile(r"^(QUESTION|OPTION|ANSWER|EXPLANATION)\s*:\s*(.*)$", re.IGNORECASE)


def parse_questions(text):
    result = ParseResult()
    current = None
    section = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line == "---":
            continue
        match = PREFIX.match(line)
        if not match:
            if current is not None and section == "EXPLANATION":
                current["explanation"] = "\n".join(
                    part for part in (current["explanation"], line) if part
                )
            else:
                result.errors.append(
                    ParseError(
                        number, "Expected QUESTION:, OPTION:, ANSWER:, EXPLANATION:, or ---."
                    )
                )
            continue
        key, value = match.group(1).upper(), match.group(2).strip()
        section = key
        if key == "QUESTION":
            if current is not None:
                _finish(current, result)
            current = {
                "text": value,
                "options": [],
                "answer": None,
                "answer_seen": False,
                "explanation": "",
                "line": number,
            }
        elif current is None:
            result.errors.append(ParseError(number, f"{key}: must follow QUESTION:."))
        elif key == "OPTION":
            current["options"].append(value)
        elif key == "ANSWER":
            if current["answer_seen"]:
                result.errors.append(
                    ParseError(number, "ANSWER may only appear once per question.")
                )
                continue
            current["answer_seen"] = True
            try:
                current["answer"] = int(value)
            except ValueError:
                result.errors.append(
                    ParseError(number, "ANSWER must be a one-based option number.")
                )
        elif key == "EXPLANATION":
            current["explanation"] = value
    if current is not None:
        _finish(current, result)
    if not text.strip():
        result.errors.append(ParseError(1, "The document is empty."))
    return result


def _finish(data, result):
    line = data["line"]
    valid = True
    if not data["text"]:
        result.errors.append(ParseError(line, "Question text is required."))
        valid = False
    if len(data["options"]) < 4:
        result.errors.append(ParseError(line, "Each question requires at least four options."))
        valid = False
    if any(not option for option in data["options"]):
        result.errors.append(ParseError(line, "Options cannot be empty."))
        valid = False
    if data["answer"] is None:
        result.errors.append(ParseError(line, "ANSWER is required."))
        valid = False
    elif not 1 <= data["answer"] <= len(data["options"]):
        result.errors.append(ParseError(line, "ANSWER does not identify an available option."))
        valid = False
    if valid:
        result.questions.append(
            ParsedQuestion(data["text"], data["options"], data["answer"], data["explanation"], line)
        )
