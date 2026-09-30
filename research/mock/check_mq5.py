#!/usr/bin/env python3
"""Syntax/type-check MQL5 sources by translating them to C++ and compiling with g++ -fsyntax-only.

Only a first-pass net: catches typos, undeclared identifiers, wrong arity and type errors.
It cannot know every MetaEditor rule (-Wshadow mirrors MetaEditor's "declaration hides ..." warning).
Always compile in MetaEditor too.

usage: check_mq5.py file.mq5 [file2.mq5 ...]
"""
import os, re, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MOCK = os.path.join(ROOT, "research", "mock", "mql5_mock.h")
INC = os.path.join(ROOT, "src")

def translate(src: str) -> str:
    out = []
    for line in src.splitlines():
        t = line.strip()
        if t.startswith("#property"):
            out.append("")
            continue
        if t.startswith("input group"):
            out.append("")
            continue
        m = re.match(r'#include\s*<(XAU/[^>]+)>', t)
        if m:
            out.append('#include "%s"' % os.path.join(INC, os.path.basename(m.group(1))))
            continue
        if re.match(r'#include\s*<Trade/Trade.mqh>', t):
            out.append("")
            continue
        # array parameters:  const T &name[]  ->  const std::vector<T> &name
        line = re.sub(r'\bconst\s+(\w+)\s*&\s*(\w+)\s*\[\]', r'const std::vector<\1> &\2', line)
        line = re.sub(r'(?<!const )\b(\w+)\s*&\s*(\w+)\s*\[\]', r'std::vector<\1> &\2', line)
        # global buffer declarations:  double A[], B[];
        if re.match(r'^(double|int|long|datetime)\s+\w+\[\](\s*,\s*\w+\[\])*\s*;', line):
            typ = line.split()[0]
            names = re.findall(r'(\w+)\[\]', line)
            line = "std::vector<%s> %s;" % (typ, ", ".join(names))
        line = re.sub(r'\b(Mql\w+)\s+(\w+)\[\]\s*;', r'std::vector<\1> \2;', line)
        line = re.sub(r'\bstring\s+(\w+)\[\]\s*;', r'std::vector<string> \1;', line)
        out.append(line)
    return "\n".join(out)

def main(files):
    rc = 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            body = translate(fh.read())
        prelude = '#include "%s"\n' % MOCK
        tail = "\nint main() { return 0; }\n"
        with tempfile.NamedTemporaryFile("w", suffix=".cpp", delete=False) as tmp:
            tmp.write(prelude + body + tail)
            path = tmp.name
        r = subprocess.run(["g++", "-std=c++17", "-fsyntax-only", "-Wall", "-Wextra", "-Wshadow", "-Wno-unused-parameter",
                            "-Wno-unused-variable", "-Wno-unused-function", path], capture_output=True, text=True)
        name = os.path.basename(f)
        if r.returncode != 0:
            rc = 1
            print("== %s: FAILED ==" % name)
            print(r.stderr.replace(path, name + "(translated)")[:6000])
        else:
            warns = r.stderr.count("warning:")
            print("== %s: OK (%d warnings) ==" % (name, warns))
            if warns:
                print(r.stderr.replace(path, name + "(translated)")[:3000])
        os.unlink(path)
    return rc

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
