from swarmcraft.btree.genetics import *
from swarmcraft.btree.nodes.actuation import *
from swarmcraft.btree.nodes.sensing import *

def check_parens(s):
    st = []
    for c in s:
        if c in '({[':
            st.append(c)

        elif c in ')}]':
            if not st or (c == ')' and st[-1] != '(') or (c == ']' and st[-1] != '[') or (c == '}' and st[-1] != '{'):
                return False
            st.pop()
    return not st

def check_equal(s1, s2):
    i = 0
    for c1, c2 in zip(s1, s2):
        if c1 != c2:
            return i
        i += 1
    if len(s1) != len(s2):
        return min(len(s1), len(s2))
    return -1

add_terminals([PressDir, ReleaseDir, Stop, Look, Rotate, StartDig, StopDig, SelectSlot, SendMessage, SendChat, PlaceHeldItem,
               IsDigging, IsKeyDown, IsHoldingItem, IsHoldingTool, IsLookingAtBlock, ClearChatQueue, ClearMessageQueue, GotMessage, GotChat])

num_tests = 100
ok = True
failed = []

for i in range(num_tests):
    tree = generate_maxdepth(2, None)
    dna = str(tree)

    tree2 = read_genome(dna, None)
    dna2 = str(tree2)


    equality = check_equal(dna, dna2)
    parens = check_parens(dna)
    parens2 = check_parens(dna2)

    if equality != -1:
        print(f'{i}: equality check failed at position {equality}')
    if not parens:
        print(f'{i}: parens check failed on original tree')
    if not parens2:
        print(f'{i}: parens check failed on reconstructed tree')
    if equality != -1 or not parens or not parens2:
        failed.append(i)
        print('first:', dna)
        print('second:', dna2)

if not failed:
    print('all tests passed')
else:
    print('failed tests:', [t for t in failed])
    print(f'{len(failed) / num_tests}')
