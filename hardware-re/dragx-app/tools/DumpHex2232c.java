import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;

public class DumpHex2232c extends GhidraScript {
    @Override
    public void run() throws Exception {
        long[] addrs = {
            0x000434e0L, 0x00043500L, 0x00043526L, 0x00043540L,
            0x00043555L, 0x00043570L, 0x000435a6L, 0x000435c0L,
            0x000435e0L, 0x000435f0L
        };
        Memory mem = currentProgram.getMemory();
        for (long a : addrs) {
            Address addr = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(a);
            StringBuilder sb = new StringBuilder();
            int n = 40;
            for (int i = 0; i < n; i++) {
                byte b = mem.getByte(addr.add(i));
                sb.append(String.format("%02x ", b & 0xff));
            }
            println(String.format("0x%08x = %s", a, sb.toString()));
        }
    }
}
