import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;

public class DecompileFun2232c extends GhidraScript {
    @Override
    public void run() throws Exception {
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        decomp.setOptions(new ghidra.app.decompiler.DecompileOptions());

        String[] targets = {"FUN_0002232c", "FUN_00025e30"};
        for (String name : targets) {
            Function f = null;
            for (Function fn : currentProgram.getFunctionManager().getFunctions(true)) {
                if (fn.getName().equals(name)) {
                    f = fn;
                    break;
                }
            }
            if (f == null) {
                println("Function " + name + " not found by name, trying address lookup");
                continue;
            }
            println("=== FUNCTION: " + name + " @ " + f.getEntryPoint() + " ===");
            DecompileResults res = decomp.decompileFunction(f, 120, new ghidra.util.task.ConsoleTaskMonitor());
            if (res != null && res.decompileCompleted()) {
                println(res.getDecompiledFunction().getC());
            } else {
                println("DECOMPILE FAILED: " + (res != null ? res.getErrorMessage() : "null result"));
            }
            println("=== END ===");
        }
        decomp.dispose();
    }
}
