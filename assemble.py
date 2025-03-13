import mcschematic
import sys
import json
from pathlib import Path

DEBUG = False
# Config file path
CONFIG_FILE = Path("cyms_assembler_config.json")

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"output_path": ""}
    return {"output_path": ""}

schem = mcschematic.MCSchematic()

config = load_config()

# Process CLI arguments
if len(sys.argv) == 2:
    filePath = sys.argv[1]

    # Check if there is a saved output path
    if not config["output_path"]:
        print("No saved output path found. Please specify an output path:")
        print("Usage: python assemble.py <input_file> <output_file>")
        sys.exit(1)

    outputPath = config["output_path"]
    print(f"Using saved output path: {outputPath}")

elif len(sys.argv) == 3:
    filePath = sys.argv[1]
    outputPath = str(Path(sys.argv[2]).resolve())

    # Save the output path for future use
    config["output_path"] = outputPath
    save_config(config)
    print(f"Saved output path for future use: {outputPath}")

else:
    print("Usage:")
    print("  First time: python assemble.py <input_file> <output_file>")
    print("  Subsequent times: python assemble.py <input_file>")
    sys.exit(1)

file = open(filePath, "r")
lines = file.readlines()
file.close()

instructions = []
fileLineNumber = 0
lineNumber = 0
constants = {}

opcodes = {
    "NOP": [0, 0],
    "CPY": [1, 2],
    "SWP": [2, 2],
    "ADD": [3, 3],
    "SUB": [4, 3],
    "INC": [5, 1],
    "DEC": [6, 1],
    "MUL": [7, 3],
    "DIV": [8, 3],
    "MOD": [9, 3],
    "AND": [10, 3],
    "ORR": [11, 3],
    "XOR": [12, 3],
    "NOT": [13, 2],
    "JMP": [14, 1],
    "BRG": [15, 3],
    "BNG": [16, 3],
    "BRE": [17, 3],
    "BNE": [18, 3],
    "BRL": [19, 3],
    "BNL": [20, 3],
    "BRO": [21, 1],
    "BNO": [22, 1],
    "JSR": [23, 1],
    "RTS": [24, 0],
    "PSH": [25, 1],
    "POP": [26, 1],
    "RNG": [27, 1],
    "INP": [28, 1],
    "OUT": [29, 1],
    "LOG": [30, 1],
    "DRW": [31, 5],
    "SFX": [32, 1],
    "HLT": [33, 0]
}

for line in lines:
    fileLineNumber += 1
    line = line.strip().split("//", 1)[0]
    if line == "":
        continue
    if line.startswith(".const"):
        parts = line.split(" ")
        if len(parts) != 3:
            print(f"Error on line {fileLineNumber}: Invalid syntax {line}")
            sys.exit(1)
        name = parts[1]
        value = parts[2]
        constants[name] = value
    elif line.startswith("@"):
        parts = line.split(" ")
        if len(parts) != 1 or len(parts[0]) == 1:
            print(f"Error on line {fileLineNumber}: Invalid syntax {line}")
            sys.exit(1)
        name = parts[0]
        constants[name] = str(lineNumber)
    elif line.startswith("LOG"):
        parts = line.split(" ", 1)
        if len(parts) != 2:
            print(f"Error on line {fileLineNumber}: Invalid syntax {line}")
            sys.exit(1)
        instruction = ["LOG"]
        instruction += ["0"] * (5)
        instruction.append(parts[1].replace(" ", "_").replace("(", "").replace(")", "").replace(",", "").replace(":", ""))
        instructions.append(instruction)
        lineNumber += 1
    else:
        instruction = line.split(" ")
        if instruction[0] not in opcodes:
            print(f"Error on line {fileLineNumber}: Invalid opcode {instruction[0]}")
            sys.exit(1)
        if len(instruction) != opcodes[instruction[0]][1] + 1:
            print(f"Error on line {fileLineNumber}: Invalid number of arguments for {instruction[0]}")
            sys.exit(1)
        instruction += ["0"] * (6 - len(instruction))
        instruction += ["_"]
        instructions.append(instruction)
        lineNumber += 1


MAX_COMMANDS_PER_TOWER = 300
X_OFFSET = -2

schem.setBlock((X_OFFSET, 0, 0), 'command_block[facing=up]{Command:"say Killing all markers"}')
schem.setBlock((X_OFFSET, 1, -0), 'chain_command_block[facing=up]{Command:"kill @e[type=marker]",auto:1b}')

if DEBUG:
    print(instructions)
    print(constants)

for index, instruction in enumerate(instructions):
    opcode = opcodes[instruction[0]][0]
    modes = [0] * 5

    for i in range(1, 6):
        modes[i - 1] += instruction[i].count('#')
        modes[i - 1] += instruction[i].count('$') * 2
        instruction[i] = instruction[i].replace('$', '').replace('#', '')
        if instruction[i] in constants:
            instruction[i] = constants[instruction[i]]

        for character in instruction[i]:
            if not (character.isdigit() or character == '-'):
                print(f"Error: Invalid argument {character} for {instruction[0]}")
                sys.exit(1)

    if DEBUG:
        print(index, opcode, instruction)
    command = f'summon marker 16 {index} 0 {{Tags:[inst,persistent],CustomName:{instruction[6]},data:{{opcode:{opcode},operand1:{instruction[1]},operand2:{instruction[2]},operand3:{instruction[3]},operand4:{instruction[4]},operand5:{instruction[5]},mode1:{modes[0]},mode2:{modes[1]},mode3:{modes[2]},mode4:{modes[3]},mode5:{modes[4]}}}}}'
    schem.setBlock((X_OFFSET -index // MAX_COMMANDS_PER_TOWER, index % MAX_COMMANDS_PER_TOWER + 1, 2), f'chain_command_block[facing=up]{{Command:"{command}",auto:1b}}')

for i in range(len(instructions) // MAX_COMMANDS_PER_TOWER + 1):
    schem.setBlock((X_OFFSET -i, 0, 2), f'command_block[facing=up]{{Command:"say Instruction Tower {i + 1}"}}')

schem.setBlock((X_OFFSET, 0, 4), 'command_block[facing=up]{Command:"say Setting Scoreboards"}')
schem.setBlock((X_OFFSET, 1, 4), 'chain_command_block[facing=up]{Command:"execute as @e[tag=inst] store result score @s opcode run data get entity @s data.opcode",auto:1b}')
for i in range(1, 6):
    schem.setBlock((X_OFFSET, i + 1, 4), f'chain_command_block[facing=up]{{Command:"execute as @e[tag=inst] store result score @s operand{i} run data get entity @s data.operand{i}",auto:1b}}')
for i in range(1, 6):
    schem.setBlock((X_OFFSET, i + 6, 4), f'chain_command_block[facing=up]{{Command:"execute as @e[tag=inst] store result score @s mode{i} run data get entity @s data.mode{i}",auto:1b}}')
schem.setBlock((X_OFFSET, 12, 4), 'chain_command_block[facing=up]{Command:"execute as @e[tag=inst] run data remove entity @s data",auto:1b}')

schemName = Path(filePath).stem
# /home/user/.local/share/PrismLauncher/instances/Adrenaline(1)/minecraft/config/worldedit/schematics/
schem.save(outputPath, schemName, version=mcschematic.Version.JE_1_20_1)
print(f'Schematic saved as "{schemName}"')
