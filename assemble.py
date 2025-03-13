import mcschematic
import sys
import json
from pathlib import Path

DEBUG = True
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

unprocessedInstructions = []
instructions = []
fileLineNumber = 0
lineNumber = 0
constants = {
    "X": -1, # Index register address
    "T": -2 # Time register address
}

opcodes = {
    "NOP": ["0", 0],
    "CPY": ["1", 2],
    "SWP": ["2", 2],
    "ADD": ["3", 3],
    "SUB": ["4", 3],
    "INC": ["5", 1],
    "DEC": ["6", 1],
    "MUL": ["7", 3],
    "DIV": ["8", 3],
    "MOD": ["9", 3],
    "AND": ["10", 3],
    "ORR": ["11", 3],
    "XOR": ["12", 3],
    "NOT": ["13", 2],
    "JMP": ["14", 1],
    "BRG": ["15", 3],
    "BNG": ["16", 3],
    "BRE": ["17", 3],
    "BNE": ["18", 3],
    "BRL": ["19", 3],
    "BNL": ["20", 3],
    "BRO": ["21", 1],
    "BNO": ["22", 1],
    "JSR": ["23", 1],
    "RTS": ["24", 0],
    "PSH": ["25", 1],
    "POP": ["26", 1],
    "RNG": ["27", 3],
    "INP": ["28", 1],
    "OUT": ["29", 1],
    "LOG": ["30", 0],
    "DRW": ["31", 5],
    "SFX": ["32", 1],
    "HLT": ["33", 0]
}

def sanitize(string):
    return string.replace(" ", "_").replace(":", "").replace("\"", "").replace(",", "")

def parseLine(line):
    splitLine = line.split(" ")
    if splitLine[0] not in opcodes:
        print(f"Error on instruction {line}: Invalid instruction {splitLine[0]}")
        sys.exit(1)
    instruction = [splitLine[0]]

    if instruction[0] == "LOG":
        instruction.append(sanitize(line.split(" ", 1)[1]))
        splitLine = [splitLine[0]]
    else:
        instruction.append("_")

    if len(splitLine) != opcodes[instruction[0]][1] + 1:
        print(f"Error on instruction {line}: Incorrect operand count")
        sys.exit(1)

    for arg in splitLine[1:]:
        if arg.startswith("#$$"):
            mode = 5
        elif arg.startswith("$$"):
            mode = 4
        elif arg.startswith("#$"):
            mode = 3
        elif arg.startswith("$"):
            mode = 2
        elif arg.startswith("#"):
            mode = 1
        else:
            mode = 0
        arg = arg.lstrip("#$")
        if arg in constants:
            arg = constants[arg]
        try:
            operand = str(int(arg))
        except ValueError:
            print(f"Error on instruction {line}: Invalid argument {arg}")
            sys.exit(1)

        instruction.append([operand, mode])

    instruction += [["0", "-1"]] * (7 - len(instruction))
    if DEBUG:
        print(f"Instruction: {instruction}")
    instruction[0] = opcodes[instruction[0]][0]
    # [opcode, logText, [operand1, mode1], [operand2, mode2], [operand3, mode3], [operand4, mode4], [operand5, mode5]] 
    return instruction

for line in lines:
    fileLineNumber += 1
    line = line.split("//", 1)[0].strip()
    if line == "":
        continue
    if line.startswith(".const"):
        parts = line.split(" ")
        if len(parts) != 3:
            print(f"Error on line {fileLineNumber}: Invalid syntax {line}")
            sys.exit(1)
        constants[parts[1]] = int(parts[2])
    elif line.startswith("@"):
        parts = line.split(" ")
        if len(parts) != 1 or len(parts[0]) == 1:
            print(f"Error on line {fileLineNumber}: Invalid syntax {line}")
            sys.exit(1)
        constants[parts[0]] = lineNumber
    else:
        unprocessedInstructions.append(line)
        lineNumber += 1

for line in unprocessedInstructions:
    instructions.append(parseLine(line))

MAX_COMMANDS_PER_TOWER = 300
X_OFFSET = -2

schem.setBlock((X_OFFSET, 0, 0), 'command_block[facing=up]{Command:"say Killing all markers"}')
schem.setBlock((X_OFFSET, 1, -0), 'chain_command_block[facing=up]{Command:"kill @e[type=marker]",auto:1b}')

if DEBUG:
    #print(instructions)
    print(constants)

for index, instruction in enumerate(instructions):
    command = f'summon marker 16 {index} 0 {{Tags:[inst,persistent],CustomName:{instruction[1]},data:{{opcode:{instruction[0]},operand1:{instruction[2][0]},operand2:{instruction[3][0]},operand3:{instruction[4][0]},operand4:{instruction[5][0]},operand5:{instruction[6][0]},mode1:{instruction[2][1]},mode2:{instruction[3][1]},mode3:{instruction[4][1]},mode4:{instruction[5][1]},mode5:{instruction[6][1]}}}}}'
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
