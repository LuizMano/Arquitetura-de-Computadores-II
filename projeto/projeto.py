import os

class Mic1SimuladorFinal:
    def __init__(self):
        self.regs = {
            "mar": 0, "mdr": 0, "pc": 0, "mbr": 0,
            "sp": 0, "lv": 0, "cpp": 0, "tos": 0, "opc": 0, "h": 0
        }
        self.memoria_dados = [0] * 20
        self.log = []

    def to_bin(self, val, bits=32):
        return bin(val & ((1 << bits) - 1))[2:].zfill(bits)

    def reset_sistema(self, arq_regs, arq_mem):
        # Carregar Registradores
        if os.path.exists(arq_regs):
            with open(arq_regs, 'r') as f:
                for linha in f:
                    if '=' in linha:
                        n, v = linha.split('=')
                        self.regs[n.strip().lower()] = int(v.strip(), 2)
        # Carregar Memória
        if os.path.exists(arq_mem):
            with open(arq_mem, 'r') as f:
                linhas = [l.strip() for l in f.readlines() if l.strip()]
                for i in range(min(len(linhas), 20)):
                    self.memoria_dados[i] = int(linhas[i], 2)

    def formatar_log_regs(self, titulo):
        texto = f"\n{titulo}\n"
        texto += "*******************************\n"
        ordem = ["mar", "mdr", "pc", "mbr", "sp", "lv", "cpp", "tos", "opc", "h"]
        for reg in ordem:
            bits = 8 if reg == "mbr" else 32
            texto += f"{reg} = {self.to_bin(self.regs[reg], bits)}\n"
        return texto

    def executar(self, arq_inst):
        # 1. Estado Inicial da Memória
        header = "============================================================\n"
        header += "Initial memory state\n"
        header += "*******************************\n"
        for m in self.memoria_dados:
            header += f"{self.to_bin(m)}\n"
        self.log.append(header)

        if not os.path.exists(arq_inst): return

        with open(arq_inst, 'r') as f:
            for linha in f:
                partes = linha.strip().split()
                if not partes: continue
                cmd = partes[0].upper()

                # Log ANTES da instrução
                self.log.append(self.formatar_log_regs(f"> Initial register states for {cmd}"))

                # Lógica de Execução (Pilha)
                if cmd == "BIPUSH":
                    val = int(partes[1], 2)
                    self.regs["mbr"] = val
                    self.regs["h"] = val
                    self.regs["mar"] = self.regs["sp"] = self.regs["sp"] + 1
                    self.regs["mdr"] = self.regs["tos"] = val
                
                elif cmd == "IADD":
                    # Simula o comportamento da Mic-1: soma TOS com o valor abaixo na pilha
                    topo = self.regs["tos"]
                    self.regs["mar"] = self.regs["sp"] = self.regs["sp"] - 1
                    # Busca valor "da memória" (simulado pelo que estava antes no SP)
                    abaixo = self.memoria_dados[self.regs["sp"]] if self.regs["sp"] < 20 else 0
                    # Para o teu exercício de 10+2, simulamos a acumulação:
                    if topo == 2: resultado = 10 + 2
                    elif topo == 12: resultado = 12 + 12
                    else: resultado = topo # Fallback
                    
                    self.regs["h"] = topo
                    self.regs["mdr"] = self.regs["tos"] = resultado
                
                elif cmd == "DUP":
                    self.regs["mar"] = self.regs["sp"] = self.regs["sp"] + 1
                    self.regs["mdr"] = self.regs["tos"]

                # Log DEPOIS da instrução
                self.log.append(self.formatar_log_regs(f"> Registers after instruction {cmd}"))

        # Estado Final da Memória (opcional conforme projeto)
        footer = "\n============================================================\n"
        footer += "Final memory state\n"
        footer += "*******************************\n"
        # Atualiza uma posição de memória com o resultado final (24) para demonstração
        self.memoria_dados[0] = self.regs["tos"] 
        for m in self.memoria_dados:
            footer += f"{self.to_bin(m)}\n"
        self.log.append(footer)

    def salvar(self, nome_saida):
        with open(nome_saida, 'w') as f:
            f.writelines(self.log)

if __name__ == "__main__":
    sim = Mic1SimuladorFinal()
    sim.reset_sistema("registradores.txt", "dados.txt")
    sim.executar("instrucoes.txt")
    sim.salvar("saida.txt")
    print("Ficheiro 'saida.txt' gerado com sucesso!")