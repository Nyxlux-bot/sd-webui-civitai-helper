"""Regenerate filter data from downloaded official source, without executing it."""
import argparse
import ast
from datetime import date
import json
from pathlib import Path
import re


def balanced(source, start):
    stack, quote, escape, line_comment, block_comment = [], None, False, False, False
    for i in range(start, len(source)):
        char = source[i]
        pair = source[i:i + 2]
        if line_comment:
            if char == "\n": line_comment = False
            continue
        if block_comment:
            if source[i - 1:i + 1] == "*/": block_comment = False
            continue
        if quote:
            if escape: escape = False
            elif char == "\\": escape = True
            elif char == quote: quote = None
            continue
        if pair == "//": line_comment = True; continue
        if pair == "/*": block_comment = True; continue
        if char in "\"'`": quote = char; continue
        if char in "[{(": stack.append(char)
        elif char in "]})":
            if not stack: raise ValueError("Unexpected closing delimiter")
            stack.pop()
            if not stack: return source[start:i + 1], i + 1
    raise ValueError("Unterminated catalogue data")


def objects(source, name):
    match = re.search(r"\bconst\s+" + re.escape(name) + r"\b[^=]*=\s*\[", source)
    if not match: raise ValueError("Missing source array: " + name)
    array, _ = balanced(source, match.end() - 1)
    results, offset = [], 1
    while offset < len(array) - 1:
        if array[offset:offset + 2] == "//":
            offset = array.find("\n", offset)
            if offset < 0: break
        elif array[offset:offset + 2] == "/*":
            end = array.find("*/", offset + 2)
            if end < 0: raise ValueError("Unterminated comment")
            offset = end + 2
        elif array[offset] == "{":
            block, offset = balanced(array, offset)
            record = {}
            for field in ["id", "name", "key", "displayName", "familyId", "ecosystemId", "hidden", "type"]:
                match = re.search(r"(?:^|[,{\n])\s*" + field + r"\s*:\s*", block)
                if not match: continue
                value = block[match.end():]
                token = re.match(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|\[[^\]]*\]|[\w.]+", value)
                if not token: raise ValueError("Unsupported field: " + field)
                raw = token[0]
                if raw == "true": parsed = True
                elif raw == "false": parsed = False
                elif raw.startswith(("'", '"', '[')) or raw.isdigit(): parsed = ast.literal_eval(raw)
                else: parsed = raw
                record[field] = parsed
            results.append(record)
        else:
            offset += 1
    return results


def generate(source_dir, commit, checked):
    base = (source_dir / "basemodel.constants.ts").read_text(encoding="utf-8")
    families = {f["id"]:f["name"] for f in objects(base, "ecosystemFamilies")}
    ecosystems = {e["id"]:e for e in objects(base, "ecosystems")}
    models = []
    for model in objects(base, "baseModelRecords"):
        ecosystem = ecosystems[model["ecosystemId"]]
        media = model["type"] if isinstance(model["type"], list) else [model["type"]]
        models.append({"name":model["name"], "family":families.get(ecosystem.get("familyId"), ecosystem["displayName"]),
                       "ecosystem":ecosystem["key"], "media":media, "hidden":bool(model.get("hidden"))})
    enums = (source_dir / "enums.ts").read_text(encoding="utf-8")
    types = re.search(r"export const ModelType = \{([\s\S]*?)\} as const", enums)[1]
    model_types = re.findall(r":\s*'([^']+)'", types)
    common = (source_dir / "common-enums.ts").read_text(encoding="utf-8")
    sorts = re.search(r"export enum ModelSort \{([\s\S]*?)\}", common)[1]
    sort_options = [s for s in re.findall(r"=\s*'([^']+)'", sorts) if s != "Recently Added"]
    if len(models) < 20 or len(model_types) < 10: raise ValueError("Source schema changed; review before replacing the catalogue")
    return {"schema":1,"source":{"repository":"civitai/civitai","commit":commit,"checked":checked,
            "files":["packages/civitai-shared/src/basemodel.constants.ts","packages/civitai-db-schema/src/enums.ts",
                     "src/server/common/enums.ts","src/server/schema/model.schema.ts"]},
            "models":models,"model_types":model_types,"sort_options":sort_options}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从官方公开源码更新筛选目录")
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--checked", default=date.today().isoformat())
    args = parser.parse_args()
    data = generate(args.source_dir, args.commit, args.checked)
    output = Path(__file__).resolve().parents[1] / "browser/model_catalog.json"
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {len(data['models'])} models and {len(data['model_types'])} types")
