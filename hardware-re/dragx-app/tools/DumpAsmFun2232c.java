import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.Memory;

public class DumpAsmFun2232c extends GhidraScript {
    @Override
    public void run() throws Exception {
        Function f = null;
        for (Function fn : currentProgram.getFunctionManager().getFunctions(true)) {
            if (fn.getName().equals("FUN_0002232c")) { f = fn; break; }
        }
        if (f == null) { println("not found"); return; }
        Memory mem = currentProgram.getMemory();
        InstructionIterator it = currentProgram.getListing().getInstructions(f.getBody(), true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            Address a = ins.getAddress();
            int len = ins.getLength();
            StringBuilder hex = new StringBuilder();
            for (int i = 0; i < len; i++) {
                hex.append(String.format("%02x", mem.getByte(a.add(i)) & 0xff));
            }
            println(String.format("%s  [%s]  %s", a, hex.toString(), ins.toString()));
        }
    }
}
