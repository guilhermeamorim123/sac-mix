import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;

public class DumpAsm extends GhidraScript {
    @Override
    public void run() throws Exception {
        Function f = getFunctionAt(toAddr(0x00025fd4L));
        if (f == null) {
            println("JNI_OnLoad not found at expected address, searching...");
            for (Function fn : currentProgram.getFunctionManager().getFunctions(true)) {
                if (fn.getName().equals("JNI_OnLoad")) {
                    f = fn;
                    break;
                }
            }
        }
        println("Function: " + f.getName() + " " + f.getBody());
        Memory mem = currentProgram.getMemory();
        InstructionIterator it = currentProgram.getListing().getInstructions(f.getBody(), true);
        while (it.hasNext()) {
            Instruction insn = it.next();
            Address addr = insn.getMinAddress();
            byte[] bytes = insn.getBytes();
            StringBuilder hex = new StringBuilder();
            for (byte b : bytes) {
                hex.append(String.format("%02x ", b));
            }
            println(String.format("%s  [%s]  %s", addr, hex.toString().trim(), insn.toString()));
        }

        println("=== Calls to FUN_0002232c ===");
        Function target = getFunctionAt(toAddr(0x0002232cL));
        if (target != null) {
            ghidra.program.model.symbol.ReferenceIterator refs =
                currentProgram.getReferenceManager().getReferencesTo(target.getEntryPoint());
            while (refs.hasNext()) {
                println("  call from: " + refs.next().getFromAddress());
            }
        }
    }
}
