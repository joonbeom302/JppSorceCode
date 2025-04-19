# j++ 인터프리터 전체 구현

import re
import sys

class JPlusPlusError(Exception):
    def __init__(self, message, line_number=None):
        if line_number is not None:
            super().__init__(f"[오류] 줄 {line_number}: {message}")
        else:
            super().__init__(f"[오류] {message}")

class JPlusPlusInterpreter:
    def __init__(self):
        self.variables = {}
        self.functions = {}
        self.lines = []
        self.current_line = 0

    def run(self, code):
        code = self.remove_multiline_comments(code)
        self.lines = code.split('\n')
        while self.current_line < len(self.lines):
            line_number = self.current_line + 1
            line = self.lines[self.current_line]
            try:
                line = self.remove_comments(line)
                if not line.strip():
                    self.current_line += 1
                    continue
                if line.strip().startswith("함수 "):
                    self.handle_function_definition(line.strip(), line_number)
                    continue
                if not (line.strip().endswith(';') or line.strip().endswith('}') or '{' in line):
                    raise JPlusPlusError("세미콜론이 필요합니다.", line_number)
                self.execute_line(line.strip().rstrip(';'), line_number)
                self.current_line += 1
            except JPlusPlusError as e:
                print(e)
                break

    def remove_comments(self, line):
        line = re.sub(r'#.*', '', line)
        line = re.sub(r'//.*', '', line)
        return line

    def remove_multiline_comments(self, code):
        return re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

    def execute_line(self, line, line_number):
        if not line:
            return
        if line.startswith("출력"):
            self.handle_print(line, line_number)
        elif line.startswith("입력"):
            self.handle_input(line, line_number)
        elif re.match(r"^(정수|소수|문자열) ", line):
            self.handle_declaration(line, line_number)
        elif re.match(r"^\w+\(.*\)$", line):
            self.handle_function_call(line)
        elif re.match(r"^[a-zA-Z_]\w* ?(\+\+|--|=|\*=|/=|\+=|-=).*$", line):
            self.handle_assignment(line, line_number)
        elif line.startswith("만약") or line.startswith("아니고 만약") or line.startswith("아니면"):
            self.handle_if(line, line_number)
        elif line.startswith("계속반복"):
            self.handle_while(line, line_number)
        elif line.startswith("반복"):
            self.handle_for(line, line_number)
        elif line == '}':
            return
        else:
            raise JPlusPlusError("알 수 없는 문장입니다.", line_number)

    def handle_block(self):
        block = []
        self.current_line += 1
        while self.current_line < len(self.lines):
            line = self.remove_comments(self.lines[self.current_line]).strip()
            if not line:
                self.current_line += 1
                continue
            if line == '}':
                break
            block.append(self.lines[self.current_line])
            self.current_line += 1
        return block

    def evaluate_condition(self, expr, line_number):
        for var in self.variables:
            expr = re.sub(rf'\b{var}\b', str(self.variables[var]), expr)
        try:
            return eval(expr, {}, {})
        except:
            raise JPlusPlusError("조건식 평가 오류입니다.", line_number)

    def handle_if(self, line, line_number):
        matched = re.match(r'(만약|아니고 만약)\((.*?)\) *{', line)
        if matched:
            keyword, cond = matched.groups()
            block = self.handle_block()
            if self.evaluate_condition(cond, line_number):
                interp = JPlusPlusInterpreter()
                interp.variables = self.variables
                interp.functions = self.functions
                interp.run('\n'.join(block))
                self.variables.update(interp.variables)
                self.skip_else_chain()
            else:
                self.skip_else_chain()
            return

        elif re.match(r'아니면 *{', line):
            block = self.handle_block()
            interp = JPlusPlusInterpreter()
            interp.variables = self.variables
            interp.functions = self.functions
            interp.run('\n'.join(block))
            self.variables.update(interp.variables)

    def skip_else_chain(self):
        while self.current_line + 1 < len(self.lines):
            next_line = self.lines[self.current_line + 1].strip()
            if next_line.startswith("아니고 만약") or next_line.startswith("아니면"):
                self.current_line += 1
                self.handle_block()
            else:
                break

    def handle_while(self, line, line_number):
        match = re.match(r'계속반복\((.*)\) *{', line)
        if not match:
            raise JPlusPlusError("반복문 문법 오류입니다.", line_number)
        cond = match.group(1)
        block = self.handle_block()
        while self.evaluate_condition(cond, line_number):
            interp = JPlusPlusInterpreter()
            interp.variables = self.variables.copy()
            interp.functions = self.functions
            interp.run('\n'.join(block))
            self.variables.update(interp.variables)

    def handle_for(self, line, line_number):
        match = re.match(r'반복\((정수 \w+ *= *\d+); *(\w+ *[<>=!]+ *\d+); *(\w+(\+\+|--|\+=\d+|-=\d+))\) *{', line)
        if not match:
            raise JPlusPlusError("반복문(for) 문법 오류입니다.", line_number)
        init, cond, update, _ = match.groups()
        self.execute_line(init + ';', line_number)
        block = self.handle_block()
        while self.evaluate_condition(cond, line_number):
            interp = JPlusPlusInterpreter()
            interp.variables = self.variables.copy()
            interp.functions = self.functions
            interp.run('\n'.join(block))
            self.variables.update(interp.variables)
            self.execute_line(update + ';', line_number)

    def handle_print(self, line, line_number):
        match = re.match(r'출력\((.*)\)', line)
        if not match:
            raise JPlusPlusError("출력 문법 오류입니다.", line_number)
        content = match.group(1)
        parts = [part.strip() for part in content.split(',')]
        output = []
        for part in parts:
            if part.startswith('"') and part.endswith('"'):
                text = part[1:-1]
                text = text.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace("\\'", "'")
                output.append(text)
            elif part in self.variables:
                output.append(str(self.variables[part]))
            else:
                raise JPlusPlusError(f"존재하지 않는 변수 '{part}'", line_number)
        print(''.join(output))

    def handle_input(self, line, line_number):
        match = re.match(r'입력\((\w+)\)', line)
        if not match:
            raise JPlusPlusError("입력 문법 오류입니다.", line_number)
        var_name = match.group(1)
        if var_name not in self.variables:
            raise JPlusPlusError(f"입력할 변수 '{var_name}'가 선언되지 않았습니다.", line_number)
        value = input()
        old_val = self.variables[var_name]
        if isinstance(old_val, int):
            self.variables[var_name] = int(value)
        elif isinstance(old_val, float):
            self.variables[var_name] = float(value)
        else:
            self.variables[var_name] = value

    def handle_declaration(self, line, line_number):
        match = re.match(r'(정수|소수|문자열) (\w+)( *= *(.*))?', line)
        if not match:
            raise JPlusPlusError("변수 선언 문법 오류입니다.", line_number)
        dtype, name, _, value = match.groups()
        if name in self.variables:
            raise JPlusPlusError(f"변수 '{name}'가 이미 선언되었습니다.", line_number)
        if value:
            value = value.strip()
            if dtype == "정수":
                self.variables[name] = int(eval(value, {}, self.variables))
            elif dtype == "소수":
                self.variables[name] = float(eval(value, {}, self.variables))
            elif dtype == "문자열":
                if not (value.startswith('"') and value.endswith('"')):
                    raise JPlusPlusError("문자열은 큰따옴표로 묶어야 합니다.", line_number)
                self.variables[name] = value[1:-1]
        else:
            self.variables[name] = 0 if dtype == "정수" else 0.0 if dtype == "소수" else ""

    def handle_assignment(self, line, line_number):
        if re.match(r'^\w+\+\+$', line.strip()):
            name = line.strip()[:-2]
            if name not in self.variables:
                raise JPlusPlusError(f"변수 '{name}'가 선언되지 않았습니다.", line_number)
            if isinstance(self.variables[name], (int, float)):
                self.variables[name] += 1
            else:
                raise JPlusPlusError("++는 정수나 소수에만 사용할 수 있습니다.", line_number)
            return
        elif re.match(r'^\w+--$', line.strip()):
            name = line.strip()[:-2]
            if name not in self.variables:
                raise JPlusPlusError(f"변수 '{name}'가 선언되지 않았습니다.", line_number)
            if isinstance(self.variables[name], (int, float)):
                self.variables[name] -= 1
            else:
                raise JPlusPlusError("--는 정수나 소수에만 사용할 수 있습니다.", line_number)
            return

        match = re.match(r'(\w+) *(\+=|-=|\*=|/=|=) *(.*)', line)
        if not match:
            raise JPlusPlusError("값 할당 문법 오류입니다.", line_number)
        name, operator, value = match.groups()
        if name not in self.variables:
            raise JPlusPlusError(f"변수 '{name}'가 선언되지 않았습니다.", line_number)
        try:
            eval_value = eval(value, {}, self.variables)
        except:
            raise JPlusPlusError("값 계산 오류입니다.", line_number)

        if operator == '=':
            self.variables[name] = eval_value
        elif operator == '+=':
            self.variables[name] += eval_value
        elif operator == '-=':
            self.variables[name] -= eval_value
        elif operator == '*=':
            self.variables[name] *= eval_value
        elif operator == '/=':
            self.variables[name] /= eval_value

    def handle_function_definition(self, line, line_number):
        match = re.match(r'함수 (\w+)\((.*?)\) *{', line)
        if not match:
            raise JPlusPlusError("함수 정의 문법 오류입니다.", line_number)
        name, params = match.groups()
        param_list = [p.strip() for p in params.split(',')] if params else []
        block = self.handle_block()
        self.functions[name] = (param_list, block)
        self.current_line += 1

    def handle_function_call(self, line, line_number=None):
        match = re.match(r'(\w+)\((.*)\)', line)
        if not match:
            raise JPlusPlusError("함수 호출 문법 오류입니다.", line_number)
        name, args = match.groups()
        if name not in self.functions:
            raise JPlusPlusError(f"정의되지 않은 함수 '{name}' 호출입니다.", line_number)
        param_list, block = self.functions[name]
        args = [arg.strip() for arg in args.split(',')] if args else []
        if len(param_list) != len(args):
            raise JPlusPlusError("인자 개수가 매개변수와 일치하지 않습니다.", line_number)
        interp = JPlusPlusInterpreter()
        for pname, arg in zip(param_list, args):
            dtype, varname = pname.split()
            if dtype == "정수":
                interp.variables[varname] = int(eval(arg, {}, self.variables))
            elif dtype == "소수":
                interp.variables[varname] = float(eval(arg, {}, self.variables))
            elif dtype == "문자열":
                interp.variables[varname] = arg.strip('"')
        interp.functions = self.functions
        interp.run('\n'.join(block))

if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].endswith(".j++"):
        print("사용법: python interpreter.py 파일명.j++")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
        interp = JPlusPlusInterpreter()
        interp.run(code)
    except FileNotFoundError:
        print(f"[오류] 파일을 찾을 수 없습니다: {filename}")
    except Exception as e:
        print(f"[오류] {e}")
