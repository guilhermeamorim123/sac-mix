import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.util.task.ConsoleTaskMonitor;

import java.util.Iterator;

public class DecompileJniOnLoad extends GhidraScript {
    @Override
    public void run() throws Exception {
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        decomp.setOptions(new ghidra.app.decompiler.DecompileOptions());

        FunctionManager fm = currentProgram.getFunctionManager();
        Iterator<Function> it = fm.getFunctions(true);
        while (it.hasNext()) {
            Function f = it.next();
            String name = f.getName();
            if (name.contains("JNI_OnLoad") || name.equals("JNI_OnLoad")) {
                println("=== FUNCTION: " + name + " @ " + f.getEntryPoint() + " ===");
                DecompileResults res = decomp.decompileFunction(f, 120, new ConsoleTaskMonitor());
                if (res != null && res.decompileCompleted()) {
                    println(res.getDecompiledFunction().getC());
                } else {
                    println("DECOMPILE FAILED: " + (res != null ? res.getErrorMessage() : "null result"));
                }
                println("=== END FUNCTION ===");
            }
        }

        // Also dump any function that calls exit() directly, for cross reference
        println("=== SEARCHING FOR exit() CALLERS ===");
        Function exitFunc = null;
        Iterator<Function> it2 = fm.getFunctions(true);
        while (it2.hasNext()) {
            Function f = it2.next();
            if (f.getName().equals("exit")) {
                exitFunc = f;
                break;
            }
        }
        if (exitFunc != null) {
            println("exit() found at: " + exitFunc.getEntryPoint());
            ghidra.program.model.symbol.ReferenceIterator refs =
                currentProgram.getReferenceManager().getReferencesTo(exitFunc.getEntryPoint());
            while (refs.hasNext()) {
                ghidra.program.model.symbol.Reference r = refs.next();
                Function caller = fm.getFunctionContaining(r.getFromAddress());
                println("  called from: " + r.getFromAddress() + " in function " + (caller != null ? caller.getName() : "?"));
            }
        } else {
            println("exit() function symbol not found directly");
        }

        decomp.dispose();
    }
}
