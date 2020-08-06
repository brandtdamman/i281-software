''' i281 Compiler for CPR E 281 '''

#> Import Statements
from types import SimpleNamespace

import argparse
import os
import platform
import sys

#> Global Variables
_variables = {}
_branch_destinations = {}

#> Argument Parser setup
_parser = argparse.ArgumentParser(description='Compile assembly code to machine code for \
    the i281 microprocessor.')
#_parser.add_argument('files', metavar='filename', nargs='+', help='File(s) to be compiled', type=str)
_parser.add_argument('-v', '--verbose', action='store_true', help='Produce a more verbose \
    output to the command line.')
_parser.add_argument('--version', action='store_true', help='Output the compiler version \
    without compiling files.')
_parser.add_argument('-i', '--input', metavar='filename', nargs='+', help='File(s) to \
    be compiled to machine language.', type=str)
_parser.add_argument('-f', '--force', action='store_true', help='Forces all CL prompts \
    to default to yes or no respectively.')

#> Constants
_DMEM_LIMIT = 16
_MAX_CODE_LENGTH = 32 # Can't exceed IMEM, sadly.

#> OPCODES
_instruction_dictionary = {
    "NOOP"      :   "0000_",
    "INPUTC"    :   "0001_",
    "INPUTCF"   :   "0001_",
    "INPUTD"    :   "0001_",
    "INPUTDF"   :   "0001_",
    "MOVE"      :   "0010_",
    "LOADI"     :   "0011_",
    "LOADP"     :   "0011_",
    "ADD"       :   "0100_",
    "ADDI"      :   "0101_",
    "SUB"       :   "0110_",
    "SUBI"      :   "0111_",
    "LOAD"      :   "1000_",
    "LOADF"     :   "1001_",
    "STORE"     :   "1010_",
    "STOREF"    :   "1011_",
    "SHIFTL"    :   "1100_",
    "SHIFTR"    :   "1100_",
    "CMP"       :   "1101_",
    "JUMP"      :   "1110_",
    "BRE"       :   "1111_",
    "BRZ"       :   "1111_",
    "BRNE"      :   "1111_",
    "BRNZ"      :   "1111_",
    "BRG"       :   "1111_",
    "BRGE"      :   "1111_"
}

_instruction_jumps = [
    "JUMP",
    "BRE",
    "BRZ",
    "BRNE",
    "BRNZ",
    "BRG",
    "BRGE"
]

#> Register values
_register_values = {
    "A"     :   "00_",
    "B"     :   "01_",
    "C"     :   "10_",
    "D"     :   "11_"
}

#> Functions
def openFile(current_file):
    ''' Opens the desired file and returns the contents in a massive string whilst closing. '''
    temp_list = current_file.readlines()

    file_string = ''
    for line in temp_list:
        file_string += line

    current_file.close()
    return file_string

def outputFile(file_lines):
    ''' Outputs the file (in string format) with line numbers. '''
    count = 0
    for line in file_lines:
        if count < 10:
            # NOTE: Add zeros instead of spaces if desired.
            print(f"  {count}| {line}")
        elif count < 100:
            print(f" {count}| {line}")
        else:
            # Presumably files won't become this large, but just in case.
            print(f"{count}| {line}")
        count += 1

def analyzeFile(file_lines):
    ''' Removes the comments from the program, so that \
        .data and .code remain to be found. '''
#    import re
    
    file_string = ''
    data_line_number = -1
    code_line_number = -1
    line_number = 0

    # Regular Expression set of all legal characters. 2020-01-05
#    expression = "[a-zA-Z0-9\s?\[\]{},.:]+"
#    expression_program = re.compile(expression)

    for line in file_lines:
        # Necessary for error handling.
        original_line = line

        # Avoid performing string manipulation unless necessary.
        if len(line) > 0 and not line[0] == '\n' and not line[0] == ';':
            # Line is more than a comment.
            # Provide spacing for analyzing instructions.
            line = line.replace(",", " , ")
            line = line.replace("]", " ] ")
            line = line.replace("[", " [ ")
            line = line.replace("}", " } ")
            line = line.replace("{", " { ")
            line = line.replace("+", " + ")
            line = line.replace("-", " - ")

            # NOTE: Needed for opcode observation.
            line = line.replace("\t", " ")

            # See if there is an in-line comment at the end of instruction.
            if line.count(';') > 0:
                line = line[:line.find(';')] + '\n'
            else:
                line += '\n'

            # Perform a regular expression check to find illegal characters.
#            result = expression_program.fullmatch(line)
#            if result is None:
#                string = produceException(message='Illegal character found', error_type='ValueError',
#                                        line_number=line_number, original_line=original_line)
#                raise Exception(string)

            # Syntax check.  Make sure there is at least a code section.
            if line.find('.data') > -1:
                # .data keyword found.  Ensure it is unique.
                if not data_line_number == -1:
                    string = produceException(message='More than one .data section exists.',
                                            error_type='SectionError', line_number=line_number,
                                            original_line=original_line)
                    raise Exception(string)
                data_line_number = line_number
            elif line.find('.code') > -1:
                # .code keyword found.  Ensure it is unique.
                if not code_line_number == -1:
                    string = produceException(message='More than one .code section exists.',
                                            error_type='SectionError', line_number=line_number,
                                            original_line=original_line)
                    raise Exception(string)
                code_line_number = line_number

            file_string += line
            line_number += 1 

    # If there was no code section, program cannot be compiled.
    # NOTE: It is possible there is no data section.
    if code_line_number == -1:
        string = produceException(message='There does not exist a .code section.',
                                error_type='SectionError')
        raise Exception(string)

    # Check length of program.  Must maintain IMEM size.
    global _MAX_CODE_LENGTH
    if line_number - code_line_number > _MAX_CODE_LENGTH:
        # TODO: Does .data come first everytime?  If not, there is a problem.
        string = produceException(message='Length of code exceeds size of IMEM.',
                                error_type='SectionError')
        raise Exception(string)

    # NOTE: This takes the string, converts to a list via splitting,
    #   and takes all but the last line, as it will be blank.
    # NOTE: It will be blank, because the last .code line added will
    #   have a \n appended to the end, causing a blank entry in the
    #   list.
    new_lines = file_string.split('\n')[:-1]
    return new_lines, data_line_number, code_line_number

def findJumpLabels(file_lines, code_line_number):
    ''' Analyze labels and calculate jumps to other parts of the code. '''
    line_number = 0
    new_lines = file_lines[:code_line_number + 1]
    jump_instruction_labels = {}

    global _branch_destinations
    for line in file_lines[code_line_number + 1:]:
        # Only in .code, may we find peace.
        if line.find(':') > -1:
            # Add only the label to the branch destinations.
            _branch_destinations[line[:line.find(':')]] = line_number
            # Reappend line without the label.
            new_lines.append(line[line.find(':') + 1:])
        else:
            # Syntax check.
            line_list = splitLine(line, '')
            if not isOpcodeValid(line_list[0]):
                string = produceException(message='Opcode is not valid', line_number=line_number,
                                        error_type='ValueError', original_line=line)
                raise Exception(string)

            # TODO: Ensure an error is thrown if there are duplicate labels.
            # Temporarily store label argument (if jump opcode) to check if label exists.
            if isJumpOpcode(line_list[0]):
                jump_instruction_labels[line_list[1]] = line_number

            new_lines.append(line)

        line_number += 1

    # Check if all labels are present in code.
    for label in jump_instruction_labels.keys():
        if _branch_destinations.get(label, 'err') == 'err':
            string = produceException(message='Jump label in use does not exist.',
                                    error_type='InstructionError',
                                    line_number=jump_instruction_labels[label])
            raise Exception(string)

    return new_lines

def isOpcodeValid(opcode):
    ''' Confirms that a given opcode is valid, or invalid. '''
    global _instruction_dictionary
    if _instruction_dictionary.get(opcode, 'err') == 'err':
        return False
    return True

def isJumpOpcode(opcode):
    '''# Confirms that a given opcode is of jump type. '''
    global _instruction_jumps
    if _instruction_jumps.count(opcode) == 0:
        return False
    return True

def splitLine(line, removal_string):
    ''' Converts string to list via splitting and lambda filtering. '''
    # NOTE: See https://stackoverflow.com/a/1157160

    # NOTE: Typically tab characters (\t) would be a problem, but they
    #   are stripped during comment removal.
    # NOTE: This removes all occurences of '' from the list.
    return list(filter((removal_string).__ne__, line.split(' ')))

def assignVariables(data_lines):
    ''' Assigns data variables within .data to an address. '''
    global _variables
    # NOTE: Variable structure (example)
    #   { 'variable_name'   :   [variable_data, data_address],
    #     'array_name'      :   [ [1, 2, 3, 4], data_address] }

    line_number = 0
    data_address_number = 0
    for line in data_lines:
        # Make life easier.
        tokens = splitLine(line, '')

        # Should have at least three or more. NOTE: Sanity-check.
        if len(tokens) < 3:
            string = produceException(message='Data is not properly formatted.',
                                    error_type='InstructionError', line_number=line_number)
            raise Exception(string)

        # Only one type allowed currently.
        if not tokens[1] == 'BYTE':
            string = produceException(message='Data is not of type BYTE.',
                                    error_type='InstructionError', line_number=line_number)
            raise Exception(string)

        if len(tokens) > 3:
            # Byte array.
            if tokens[-1] == ',':
                # TODO: Change to warning message.
                string = produceException(message='Trailing comma found in array declaration.',
                                        error_type='ValueError', line_number=line_number)
                raise Exception(string)

            values = list(filter((',').__ne__, tokens[2:]))
            
            # Ensure all values are of type integer.
            for value in values:
                if not value.isalnum():
                    temp_message = 'ISA does not support non-integer values.'
                    if not value == '?':
                        string = produceException(message=temp_message, error_type='ValueError',
                                                line_number=line_number)
                        raise Exception(string)

            # Assign variable to global container with data address.
            if value == '?':
                _variables[tokens[0]] = [0, data_address_number]
            else:
                _variables[tokens[0]] = [values, data_address_number]
            data_address_number += len(values)
        else:
            # Single value variable.
            if tokens[2] == '?':
                # Currently defaults to zero.
                _variables[tokens[0]] = [0, data_address_number]
            elif tokens[2].isdigit():
                _variables[tokens[0]] = [int(tokens[2]), data_address_number]
            else:
#                print(tokens[2])
                string = produceException(message='Data value is neither undefined nor defined.',
                                        error_type='ValueError', line_number=line_number)
                raise Exception(string)

            data_address_number += 1

        global _DMEM_LIMIT
        if len(_variables) > _DMEM_LIMIT:
#            print(_variables)
            # Must not exceed memory limit.
            string = produceException(message='Data variables exceed DMEM.',
                                    error_type='MemoryOverflow')
            raise Exception(string)

def parseCode(code_lines):
    ''' Parse assembly instructions and convert to binary machine code. '''
    global _instruction_dictionary, _instruction_switch
    line_number = 0
    machine_code = ''
    for line in code_lines:
        tokens = splitLine(line, '')
        machine_instruction = _instruction_dictionary[tokens[0]]

        # This is the funkiest piece of Python I'll probably ever write.
        # The statement is fairly normal at first: take a 'str'/string variable
        #  and append to it a value from the dictionary; however, that is where
        #  everything goes odd.  The dictionary value is actually a function
        #  that is called via the trailing ram brackets with a parameter.

        machine_instruction += str(_instruction_switch[tokens[0]](tokens[1:], line_number))
        # Python considers this to be valid. All of this to implement the
        #  equivalent of a switch statement.

        machine_code += machine_instruction + '\n'
        line_number += 1

    # Removes an extra newline character.
    return machine_code[:-1]

def interpretBracket(tokens, line_number, left_bracket='[', right_bracket=']',
                    is_there_register=False, throw_boundry_error=True):
    ''' Parses information within a set of brackets <[], {}>. '''
    # NOTE: Always odd.
    #  Possible structures                      | Length
    #   [ DataAddress ]                         -   3
    #   [ DataAddress + Register ]              -   5
    #   [ DataAddress + Register +/- Offset ]   -   7
    #   { DataAddress }                         -   3
    #   { DataAddress + Offset }                -   5

    if len(tokens) < 3:
        string = produceException(message='Invalid number of arguments.',
                                error_type='ArgumentError', line_number=line_number)
        raise Exception(string)

    if tokens[0] != left_bracket:
        string = produceException(message='Invalid left bracket found in instruction.',
                                error_type='ArgumentError', line_number=line_number)
        raise Exception(string)

    # Grab the data address.
    variable_value = findDataAddress(tokens[1], line_number)

    # NOTE: If a register is grabbed, an offset must be provided 
    #   for finding the offset.
    register_value = None
    token_offset = 0
    if is_there_register:
        # + Register <+/- Offset> ]
        if not tokens[2] == '+':
            string = produceException(message='Operator ( + ) is missing from arguments.',
                                    error_type='ArgumentError', line_number=line_number)
            raise Exception(string)
        register_value = grabRegisterAddress(tokens[3], line_number)
        token_offset = 2

    # See if there is an offset for the bracket.
    current_offset = variable_value
    was_address_offset = False
    if not is_there_register and len(tokens) == 5 or is_there_register and len(tokens) == 7:
        # Evaluates the current token to determine if there is content (offset value).
        current_token = tokens[2 + token_offset]
        if tokens[4 + token_offset] == right_bracket:
            # Confirms that the offset is an integer.
            offset = tokens[3 + token_offset]
            if not offset.isdigit():
                string = produceException(message='Offset argument is not a number.',
                                        error_type='ValueError', line_number=line_number)
                raise Exception(string)
            was_address_offset = True

            # Examines operator.
            if current_token == '+':
                current_offset += int(offset)
            elif current_token == '-':
                current_offset -= int(offset)
            else:
                # Can't do fancy division or multiplication, I guess.
                string = produceException(message=f'Invalid operator ( {current_token} ) used.',
                                        error_type='ArgumentError', line_number=line_number)
                raise Exception(string)
        elif not current_token == right_bracket:
            # An open expression, much like an unanswered question.
            string = produceException(message='Right bracket is not valid or missing.',
                                    error_type='ValueError', line_number=line_number)
            raise Exception(string)

    # Will either raise an exception or warn user about data address being
    #   outside of code boundries, if necessary.
    confirmValidAddress(current_offset, throw_boundry_error, line_number)

    # NOTE: This could be returned as a tuple, list, etc.
    #   It was chosen to use a blank object and assign attributes.
    #   This allows for expansion of assembly instructions (shouldn't happen),
    #   but it also increases readability.
    results = SimpleNamespace()
    setattr(results, 'data_address', integerToBinary(current_offset))
    setattr(results, 'was_address_offset', was_address_offset);
    setattr(results, 'register_value', register_value);
    return results
    #return [integerToBinary(current_offset), was_address_offset, register_value]

def confirmValidAddress(address, throw_boundry_error, line_number):
    ''' Observes the address given and will produce either error or warning. '''
    if address < 0 or address > 63:
        if throw_boundry_error:
            # Raise an error.
            string = produceException(message='Address is out of bounds of DMEM.',
                                    error_type='ValueError', line_number=line_number)
            raise Exception(string)
        else:
            # Sound the horn.
            #print(address)
            # TODO: Raise WARNING
            #string = produceException(message='Address might be out of bounds of DMEM',
            #                        error=False, line_number=line_number)
            #raise Exception(string)
            return

def findDataAddress(address_token, line_number):
    ''' Navigates the current variables for a data address. '''
    global _variables
    temp_address = _variables.get(address_token, 'err')
    if temp_address == 'err':
        string = produceException(message='No data allocated with variable name used.',
                                error_type='ArgumentError', line_number=line_number)
        raise Exception(string)

    # NOTE: Second list item is the data address, not the first.
    return temp_address[1]

def grabRegisterAddress(register_token, line_number):
    ''' Returns the two-bit register value for the built-in registers. '''
    global _register_values
    register = _register_values.get(register_token, 'err')
    if register == 'err':
        string = produceException(message=f'Register [ {register_token} ] does not exist.',
                                error_type='ArgumentError', line_number=line_number)
        raise Exception(string)

    return register

def integerToBinary(value):
    ''' Converts the given value to binary via bit-wise mask. '''
    # Will be working with integers and will need a string _briefly_.
    if type(value) is not int:
        value = int(value)
    string_value = str(value)

    # Confirm that the given value is valid.
    if string_value[0] == '-' and not string_value[1:].isdigit():
        string = produceException(message=f'Negative integer given ( {string_value} ) is invalid.',
                                error_type='ValueError')
        raise Exception(string)
    elif not string_value[0] == '-' and not string_value.isdigit():
        string = produceException(message=f'Positive integer given ( {string_value} ) is invalid.',
                                error_type='ValueError')
        raise Exception(string)
    else:
        # NOTE: This will perform a bit-wise mask upon the integer
        #   value, cast it to binary (i.e. 0b1010), and remove the
        #   unecessary first "bits" (i.e. 0b).
        intermediate_value = bin(value & 0b11111111)[2:]

        # Fills extra zeros in, when necessary.
        if len(intermediate_value) < 8:
            return '0' * (8 - len(intermediate_value)) + intermediate_value

        return intermediate_value

def parseNOOP(tokens, line_number):
    if len(tokens) > 0:
        # TODO: Change to warning.  Additional arguments can be ignored.
        string = produceException(message=f"NOOP does not have the correct number of arguments ( 0 ).",
                                error_type='ArgumentError', line_number=line_number)
        raise Exception(string)
    return '00_00_00000000'

def parseINPUTC(tokens, line_number):
    confirmInstructionLength(len(tokens), 3, 'INPUTC', line_number)
    machine_code = '00_00_'
    machine_code += interpretBracket(tokens, line_number).data_address
    return machine_code

def parseINPUTCF(tokens, line_number):
    confirmInstructionLength(len(tokens), 3, 'INPUTCF', line_number)
    results = interpretBracket(tokens, line_number, is_there_register=True)
    machine_code = results.register_value
    machine_code += '01_'
    machine_code += results.data_address
    return machine_code

def parseINPUTD(tokens, line_number):
    confirmInstructionLength(len(tokens), 3, 'INPUTD', line_number)
    machine_code = '00_10_'
    machine_code += interpretBracket(tokens, line_number).data_address
    return machine_code

def parseINPUTDF(tokens, line_number):
    confirmInstructionLength(len(tokens), 3, 'INPUTDF', line_number)
    results = interpretBracket(tokens, line_number, is_there_register=True)
    machine_code = results.register_value
    machine_code += '11_'
    machine_code += results.data_address
    return machine_code

def parseMOVE(tokens, line_number):
    return parseMACS(tokens, 'MOVE', line_number)

def parseLOADI(tokens, line_number):
    confirmInstructionLength(len(tokens), 3, 'LOADI', line_number)
    confirmComma(tokens[1], line_number)
    machine_code = grabRegisterAddress(tokens[0], line_number)
    machine_code += '00_'
    machine_code += integerToBinary(tokens[2])
    return machine_code

def parseLOADP(tokens, line_number):
    confirmInstructionLength(len(tokens), 5, 'LOADP', line_number)
    confirmComma(tokens[1], line_number)
    machine_code = grabRegisterAddress(tokens[0], line_number)
    machine_code += '00_'

    machine_code += interpretBracket(tokens[2:], line_number, left_bracket='{', right_bracket='}',
                                    throw_boundry_error=False).data_address
    return machine_code

def parseADD(tokens, line_number):
    return parseMACS(tokens, 'ADD', line_number)

def parseADDI(tokens, line_number):
    return parseSAI(tokens, 'ADDI', line_number)

def parseSUB(tokens, line_number):
    return parseMACS(tokens, 'SUB', line_number)

def parseSUBI(tokens, line_number):
    return parseSAI(tokens, 'SUBI', line_number)

def parseLOAD(tokens, line_number):
    confirmInstructionLength(len(tokens), 5, 'LOAD', line_number)
    confirmComma(tokens[1], line_number)
    machine_code = grabRegisterAddress(tokens[0], line_number)
    machine_code += '00_'

    machine_code += interpretBracket(tokens[2:], line_number).data_address
    return machine_code

def parseLOADF(tokens, line_number):
    confirmInstructionLength(len(tokens), 7, 'LOADF', line_number)
    confirmComma(tokens[1], line_number)
    machine_code = grabRegisterAddress(tokens[0], line_number)

    results = interpretBracket(tokens[2:], line_number, is_there_register=True, throw_boundry_error=False)
    machine_code += results.register_value
    machine_code += results.data_address
    return machine_code

def parseSTORE(tokens, line_number):
    confirmInstructionLength(len(tokens), 5, 'STORE', line_number)
    
    # NOTE: This should fail if there is no comma in the list.
    comma_index = tokens.index(',')
    confirmComma(tokens[comma_index], line_number)
    results = interpretBracket(tokens[:comma_index], line_number)

    offset = 0
    if results.was_address_offset: # Was there an offset in the brackets?
        offset = 2

    machine_code = grabRegisterAddress(tokens[4 + offset], line_number)
    machine_code += '00_'
    machine_code += results.data_address

    return machine_code

def parseSTOREF(tokens, line_number):
    confirmInstructionLength(len(tokens), 7, 'STOREF', line_number)
    comma_index = tokens.index(',')
    confirmComma(tokens[comma_index], line_number)
    results = interpretBracket(tokens[:comma_index], line_number, is_there_register=True)

    offset = 0
    if results.was_address_offset:
        offset = 2
    
    machine_code = grabRegisterAddress(tokens[6 + offset], line_number)
    machine_code += results.register_value
    machine_code += results.data_address

    return machine_code

def parseSHIFTL(tokens, line_number):
    return parseSHIFT(tokens, 'L', line_number)

def parseSHIFTR(tokens, line_number):
    return parseSHIFT(tokens, 'R', line_number)

def parseCMP(tokens, line_number):
    return parseMACS(tokens, 'CMP', line_number)

def parseJUMP(tokens, line_number):
    machine_code = '00_00_'
    machine_code += calculateJump(tokens, 'JUMP', line_number)
    return machine_code # Hit the hyperdrive!

def parseBRE(tokens, line_number):
    machine_code = '00_00_'
    machine_code += calculateJump(tokens, 'BRE', line_number)
    return machine_code

def parseBRNE(tokens, line_number):
    machine_code = '00_01_'
    machine_code += calculateJump(tokens, 'BRNE', line_number)
    return machine_code

def parseBRG(tokens, line_number):
    machine_code = '00_10_'
    machine_code += calculateJump(tokens, 'BRG', line_number)
    return machine_code

def parseBRGE(tokens, line_number):
    machine_code = '00_11_'
    machine_code += calculateJump(tokens, 'BRGE', line_number)
    return machine_code

def parseSHIFT(tokens, shift_type, line_number):
    ''' Handles shift instructions for both SHIFTL and SHIFTR. '''
    confirmInstructionLength(len(tokens), 1, shift_type, line_number)

    machine_code = grabRegisterAddress(tokens[0], line_number)
    if shift_type == 'L':
        machine_code += '00_00000000'
    elif shift_type == 'R':
        machine_code += '01_00000000'
    else:
        string = produceException(message='Invalid shift type given in function arguments.',
                                error_type='ProgrammerError', line_number=line_number)
        raise Exception(string)

    return machine_code

def calculateJump(jump_token, jump_type, line_number):
    ''' Using branches collected eariler, determine the data address needed. '''
    confirmInstructionLength(len(jump_token), 1, jump_type, line_number)
    if not len(jump_token) == 1:
        string = produceException(message=f"{jump_token[0]} does not have the correct number of arguments ( 1 ).",
                                error_type='ArgumentError', line_number=line_number)
        raise Exception(string)

    # Calculate the jump to lightspeed.  Or something like that.
    global _branch_destinations
    branch = _branch_destinations.get(jump_token[0], 'err')

    # NOTE: This is simply a sanity-check as of 0.4.4
    if branch == 'err':
        string = produceException(message='Jump label in use is does not exist in current program.',
                                error_type='InstructionError', line_number=line_number)
        raise Exception(string)

    # NOTE: With line_number being a zero-indexed, a plus one is necessary
    #   for proper jump calculations.
    return integerToBinary(branch - (line_number + 1))

def parseMACS(tokens, opcode, line_number):
    ''' Performs opcode parsing for MACS: MOVE, ADD, CMP, and SUB. '''
    confirmInstructionLength(len(tokens), 3, opcode, line_number)
    confirmComma(tokens[1], line_number)
    machine_code = grabRegisterAddress(tokens[0], line_number)
    machine_code += grabRegisterAddress(tokens[2], line_number)
    machine_code += '0' * 8

    return machine_code

def parseSAI(tokens, opcode, line_number):
    ''' Performs opcode parsing for SAI: SUBI and ADDI. '''
    confirmInstructionLength(len(tokens), 3, opcode, line_number)
    confirmComma(tokens[1], line_number)
    machine_code = grabRegisterAddress(tokens[0], line_number)
    machine_code += '00_'
    machine_code += integerToBinary(tokens[2])

    return machine_code

def confirmComma(comma_token, line_number):
    ''' Raises an exception if the token given is not a comma. '''
    if not comma_token == ',':
        string = produceException(message='Token is not a comma.',
                                error_type='InstructionError', line_number=line_number)
        raise Exception(string)

def confirmInstructionLength(instruction_length, required_length, opcode, line_number):
    ''' Takes the required length and ensures the instruction \
        is equal.  If not, raise. '''
    if not instruction_length >= required_length:
        string = produceException(message=f"{opcode} does not have the correct number of arguments ( {required_length} ).",
                                error_type='ArgumentError', line_number=line_number)
        raise Exception(string)

#> Global instruction switch.  MUST be placed here.
_instruction_switch = {
    "NOOP"      :   parseNOOP,
    "INPUTC"    :   parseINPUTC,
    "INPUTCF"   :   parseINPUTCF,
    "INPUTD"    :   parseINPUTD,
    "INPUTDF"   :   parseINPUTDF,
    "MOVE"      :   parseMOVE,
    "LOADI"     :   parseLOADI,
    "LOADP"     :   parseLOADP,
    "ADD"       :   parseADD,
    "ADDI"      :   parseADDI,
    "SUB"       :   parseSUB,
    "SUBI"      :   parseSUBI,
    "LOAD"      :   parseLOAD,
    "LOADF"     :   parseLOADF,
    "STORE"     :   parseSTORE,
    "STOREF"    :   parseSTOREF,
    "SHIFTL"    :   parseSHIFTL,
    "SHIFTR"    :   parseSHIFTR,
    "CMP"       :   parseCMP,
    "JUMP"      :   parseJUMP,
    "BRE"       :   parseBRE,
    "BRZ"       :   parseBRE,
    "BRNE"      :   parseBRNE,
    "BRNZ"      :   parseBRNE,
    "BRG"       :   parseBRG,
    "BRGE"      :   parseBRGE
}

def createSubDirectory(filename, force):
    ''' Creates the necessary subdirectory tree for file production. '''
    # Make output folder.
    if not os.path.exists('./output'):
        os.makedirs('./output')

    # Make the sub-output folder, specific to file name.
    # Will continue to loop until a valid response is given.
    while True:
        if os.path.exists(f'./output/{filename}') and not force:
            response = input(f'Do you wish to overwrite previously compiled \
files for {filename} [Y/N]?  ')
            if response.lower() == 'n':
                string = produceException(message='Directory already exists, aborting.',
                                        error_type='IOError')
                raise Exception(string)
            elif response.lower() == 'y':
                break
        elif not os.path.exists(f'./output/{filename}'):
            os.makedirs(f'./output/{filename}')
            break
        else:
            break

    # Files can be overwritten.
    return filename

def writeVerilogFiles(machine_code, file_location):
    ''' Writes machine code to three Verilog HDL files for Quartus Prime. '''
    global _variables
    # TODO: Add read/write permission checks (or to createSubDirectories).
    modules = {'User_Code_Low':15, 'User_Code_High':15, 'User_Data':7}
    machine_code = machine_code.split('\n')

    current_file = None
    line_number = 0
    code_length = len(machine_code)
    for module in modules.keys():
        # Write to a file, based on module name.
        current_file = open(file=file_location + module + '.v', mode='w')
        current_file.write(f'module {module}(b0I,b1I,b2I,b3I,b4I,b5I,b6I,b7I,b8I,b9I,b10I,b11I,b12I,b13I,b14I,b15I);')
        current_file.write('\r\n\r\n')

        # for (int x = 0; x < 16; x++)
        for x in range(0, 16):
            current_file.write(f'\toutput [{modules[module]}:0] b{x}I;\r\n')
        current_file.write('\n') # Extra buffer.

        section_line_number = 0
        fill_string = '0000_00_00_00000000'
        if modules[module] == 15:
            # User_Code.
            while line_number < code_length and section_line_number < 16:
                current_file.write(f"\tassign b{section_line_number}I[15:0] = 16'b{machine_code[line_number]};\r\n")
                line_number += 1
                section_line_number += 1
            
        else:
            # User_Data.  Similar, but not quite.
            for variable in _variables.keys():
                if type(_variables[variable][0]) is list:
                    # Iterate through each element of the array and assign appropriately.
                    for element in _variables[variable][0]:
                        current_file.write(f"\tassign b{section_line_number}I[7:0] = 8'b{integerToBinary(element)};")
                        current_file.write(f" //{variable}[{section_line_number}]\r\n")
                        section_line_number += 1
                else:
                    # Not an array, simple assignment.
                    current_file.write(f"\tassign b{section_line_number}I[7:0] = 8'b{integerToBinary(_variables[variable][0])};")
                    current_file.write(f" //{variable}\r\n")
                    section_line_number += 1
            # Change the section fill-in string.
            fill_string = '0' * 8

        # Fill the rest of the code section with empty values.
        while section_line_number < 16:
            current_file.write(f"\tassign b{section_line_number}I[{modules[module]}:0] = {modules[module] + 1}'b{fill_string};\r\n")
            section_line_number += 1

        # Tie off verilog file and close it.
        current_file.write('\nendmodule\r\n')
        current_file.close()

def produceException(message='Generic Error', error=True, error_type=None,
                    line_number=0, original_line=None):
    ''' Handles all error messages and returns an exception message. '''
    ex_string = None
    if line_number < 10:
        ex_string = f'ln(00{line_number}): '
    elif line_number < 100:
        ex_string = f'ln(0{line_number}): '
    else:
        ex_string = f'ln({line_number}): '

    if error:
        ex_string += 'error: '
    else:
        ex_string += 'warning: '

    ex_string += message
    if error_type:
        ex_string += f' [{error_type}]'

    if original_line:
        ex_string += f'\n{original_line}'

    return ex_string

def is_path_directory(path):
    ''' Will return true if the path given is a directory, false if file. '''
    return os.path.isdir(os.path.dirname(path)) and not os.path.isfile(path)

def catalog_directory_files(path):
    ''' Given a directory, create a list of all .asm files.'''
    file_list = []
    for sub_path in os.listdir(path):
        if not is_path_directory(sub_path):
            # File, check for .asm
            result = check_asm_file_type(sub_path)
            if result is None:
                file_list.append(f'{path}{sub_path}')
    
    return file_list

def check_asm_file_type(file_path, from_directory=False):
    ''' Checks if file is of type assembly (.asm).  If not, returns error string. '''
    file_tree = split_by_filesystem(file_path)

    if file_tree[-1].find('.asm') < 0:
        return produceException(message='File given is not an assembly file.',
        error_type='IOError')
    return None

def split_by_filesystem(file_path):
    ''' Splits the file by the appropriate folder delimiter. '''
    if platform.system() is "Windows":
        return file_path.split('\\')
    else:
        return file_path.split('/')

def main(arguments):
    ''' Compiler top-level program.  Contained within main() for reasons. '''
    failed = {}
    succeeded = {}

    # For all programs to be compiled...
    global _branch_destinations, _variables
    for source in arguments.input:
        # Determine if input is a directory.
        files_to_compile = []
        source = str(source)

        # Strips initial prefix.
        if source[:2] == './' or source[:2] == '.\\':
            source = source[2:]

        # Confirm that the file exists.
        if os.path.exists(source) is not True:
            failed[source] = produceException(message='File/Directory given is not valid or does not exist.',
            error_type='ArgumentError')
            continue

        if is_path_directory(source):
            files_to_compile = catalog_directory_files(source)
            if len(files_to_compile) == 0:
                # no assembly files found
                failed[source] = produceException(message='Directory given has no assembly file(s) within.',
                error_type='ArgumentError')
                continue
        else:
            # singleton file
            result = check_asm_file_type(source)
            if result is None:
                files_to_compile.append(source)
            else:
                failed[source] = result
                continue

        print(files_to_compile)

        for file_path in files_to_compile:
            _branch_destinations = {}
            _variables = {}

            # File is good, go ahead and compile it.
            status_message = f"========= Compiling <{file_path}>.. ========="
            print(status_message)

            # Opens file with read permissions and returns string.
            file_string = openFile(open(file=file_path, mode='r'))

            # Present the file to the user.
            file_lines = file_string.split('\n')

            # Introducing, CLI arguments!
            if arguments.verbose:
                outputFile(file_lines)
                print()

            try:
                # Begin writting to bin file.
                bin_file = None
                filename = createSubDirectory(filename=split_by_filesystem(file_path)[-1].split('.')[0],
                            force=arguments.force)

                bin_file = open(file=f'./output/{filename}/{filename}.bin', mode='w')
                bin_file.write('=======ASSEMBLY CODE======\n')
                for line in file_lines:
                    if len(line) > 1:
                        bin_file.write(line + '\n')
                bin_file.write('\n')

                # Overwrite file_lines list with no comments.  Also, find .data and .code.
                file_lines, data_line_number, code_line_number = analyzeFile(file_lines)

                # Obtain the jump, .data, and .code locations.
                # NOTE: Jumps are stored in _branch_destinations globally.
                file_lines = findJumpLabels(file_lines, code_line_number)

                # Assign all variables to data addresses.
                assignVariables(file_lines[data_line_number + 1:code_line_number])
                
                # Parse assembly instructions.
                machine_code = parseCode(file_lines[code_line_number + 1:])

                if arguments.verbose:
                    print(' == == MACHINE CODE == == ')
                    print(machine_code + '\n')

                # Write machine code to bin file.
                bin_file.write('=======MACHINE CODE=======\n')
                bin_file.write(machine_code)

                # Convert machine code to Verilog HDL for programming the i281 microprocessor.
                file_location = f'./output/{filename}/'
                writeVerilogFiles(machine_code, file_location)

                # State file is complete.
                print(f"File ({file_path}) has successfully compiled.")
                succeeded[file_path] = filename
            except Exception as ex:
                # This will also catch all programming errors as well.
                failed[file_path] = str(ex)
            finally:
                print('=' * len(status_message))
                if bin_file:
                    bin_file.close()

    # OUTPUT STRUCTURE:
    #   ./output
    #   |-> source_name/source_name.bin
    #   |-> source_name/User_Code_Low.v
    #   |-> source_name/User_Code_High.v
    #   |-> source_name/User_Data.v

    print('\n\nAll files have been processed.')
    if len(succeeded) > 0:
        print(f'Files that succeded ({len(succeeded)}):')
        for s_file in succeeded.keys():
            filename = succeeded[s_file]
            temp_string = '\t -> ' + filename + '\n'
            temp_string += '\t  -> Output: ' + '\n'
            temp_string += f'\t   => output/{filename}/{filename}.bin' + '\n'

            if arguments.verbose:
                temp_string += f'\t   => output/{filename}/User_Code_Low.v' + '\n'
                temp_string += f'\t   => output/{filename}/User_Code_High.v' + '\n'
                temp_string += f'\t   => output/{filename}/User_Data.v' + '\n'
            print(temp_string)

    if len(failed) > 0:
        print(f'Files that failed ({len(failed)}):')
        for f_file in failed.keys():
            message = failed[f_file]
            temp_string = f'{f_file}:{message}\n'
            print(temp_string)

# Required logic for displaying version number.
arguments = _parser.parse_args()
if not arguments.version:
    main(arguments)
else:
    # NOTE: Make version number changes here when possible.
    #       Ensure it reflects the manpage number as well.
    print('i281Compiler -- Version: 0.4.9')