import os

class Mic1Completa:
    def __init__(self):
        # Registradores conforme especificação [cite: 92, 93, 94]
        self.regs = {
            "H": 0, "OPC": 0, "TOS": 0, "CPP": 0,
            "LV": 0, "SP": 0, "PC": 0, "MDR": 0, "MAR": 0
        }
        self.mbr = 0
        self.memoria_dados = [0] * 8 # 8 endereços de 32 bits [cite: 149]
        self.log_buffer = []

    def reset_memoria(self, arquivo_dados):
        """Carrega estado inicial da memória de dados.txt"""
        if os.path.exists(arquivo_dados):
            with open(arquivo_dados, 'r') as f:
                # Lê apenas as primeiras 8 linhas e converte binário para int
                linhas = [l.strip() for l in f.readlines() if l.strip()]
                for i in range(min(len(linhas), 8)):
                    self.memoria_dados[i] = int(linhas[i], 2)

    def reset_registradores(self, arquivo_regs):
        """Carrega estado inicial dos registradores com tratamento de erro"""
        if os.path.exists(arquivo_regs):
            with open(arquivo_regs, 'r') as f:
                for linha in f:
                    linha = linha.strip()
                    if ':' in linha: # Garante que a linha tem o separador
                        nome, valor = linha.split(':')
                        nome = nome.strip()
                        valor = valor.strip()
                        # Converte binário para inteiro
                        if nome == "MBR": 
                            self.mbr = int(valor, 2)
                        elif nome in self.regs: 
                            self.regs[nome] = int(valor, 2)

    def ula(self, a, b, f0, f1, ena, enb, inva, inc):
        """Lógica da ULA (Etapa 1) [cite: 6, 27, 32]"""
        a_in = a if ena else 0
        b_in = b if enb else 0
        if inva: a_in = (~a_in) & 0xFFFFFFFF
        
        if f0 == 0 and f1 == 0: res = a_in & b_in
        elif f0 == 0 and f1 == 1: res = a_in | b_in
        elif f0 == 1 and f1 == 0: res = (~b_in) & 0xFFFFFFFF
        else: res = (a_in + b_in + inc) & 0xFFFFFFFF
        return res

    def executar_microinstrucao(self, m_ins_bin):
        """Executa palavra de 23 bits [cite: 145, 146]"""
        # Salva estado ANTES para o log [cite: 171, 247]
        estado_anterior = {**self.regs, "MBR": self.mbr}
        
        # Caso Especial BIPUSH (FETCH + WRITE + READ) [cite: 226, 228, 230]
        if m_ins_bin[17:19] == "11":
            byte_val = int(m_ins_bin[0:8], 2)
            self.mbr = byte_val
            self.regs["H"] = byte_val # Atribuição direta [cite: 230, 231]
            reg_b_nome = "FETCH_SPECIAL"
            regs_c_list = ["MBR", "H"]
        else:
            # Decodificação Normal
            ula_bits = m_ins_bin[0:8]
            c_bus_bits = m_ins_bin[8:17]
            mem_bits = m_ins_bin[17:19]
            b_bus_bits = m_ins_bin[19:23]

            # Barramento B [cite: 98, 99, 100]
            regs_b_map = ["MDR", "PC", "MBR", "MBRU", "SP", "LV", "CPP", "TOS", "OPC"]
            idx_b = int(b_bus_bits, 2)
            reg_b_nome = regs_b_map[idx_b] if idx_b < 9 else "NADA"
            
            val_b = self.regs.get(reg_b_nome, 0)
            if reg_b_nome == "MBR": val_b = (self.mbr ^ 0x80) - 0x80 # Sinal [cite: 101]
            elif reg_b_nome == "MBRU": val_b = self.mbr & 0xFF # Sem sinal [cite: 102]

            # ULA e Deslocador [cite: 81, 82, 84, 88]
            res = self.ula(self.regs["H"], val_b, int(ula_bits[2]), int(ula_bits[3]), int(ula_bits[4]), int(ula_bits[5]), int(ula_bits[6]), int(ula_bits[7]))
            
            if ula_bits[0] == "1": res = (res << 8) & 0xFFFFFFFF # SLL8
            elif ula_bits[1] == "1": res = (res >> 1) | (res & 0x80000000) # SRA1

            # Escrita Barramento C [cite: 104, 105, 112]
            regs_c_map = ["MAR", "MDR", "PC", "SP", "LV", "CPP", "TOS", "OPC", "H"]
            regs_c_list = []
            for i, bit in enumerate(reversed(c_bus_bits)):
                if bit == "1":
                    self.regs[regs_c_map[i]] = res
                    regs_c_list.append(regs_c_map[i])

            # Acesso à Memória [cite: 153, 154, 155]
            if mem_bits[0] == "1": # WRITE
                if 0 <= self.regs["MAR"] < 8: self.memoria_dados[self.regs["MAR"]] = self.regs["MDR"]
            if mem_bits[1] == "1": # READ
                if 0 <= self.regs["MAR"] < 8: self.regs["MDR"] = self.memoria_dados[self.regs["MAR"]]

        self.gerar_log(m_ins_bin, estado_anterior, reg_b_nome, regs_c_list)

    def gerar_log(self, ins, antes, b_bus, c_bus):
        """Gera entrada de log para cada microinstrução [cite: 170, 245, 250]"""
        log = f"Microinstrucao: {ins}\n"
        log += f"B-Bus: {b_bus} | C-Bus Habilitados: {', '.join(c_bus)}\n"
        log += f"REGS ANTES: {antes}\n"
        log += f"REGS DEPOIS: { {**self.regs, 'MBR': self.mbr} }\n"
        log += f"MEMORIA: {self.memoria_dados}\n"
        log += "-"*60 + "\n"
        self.log_buffer.append(log)

    def traduzir_e_executar(self, arquivo_ijvm):
        """Traduz IJVM para microinstruções de 23 bits [cite: 237, 243]"""
        if not os.path.exists(arquivo_ijvm): return
        
        with open(arquivo_ijvm, 'r') as f:
            for linha in f:
                partes = linha.strip().split()
                if not partes: continue
                comando = partes[0].upper()
                
                micro_sequencia = []
                if comando == "BIPUSH": # [cite: 221, 222, 236]
                    val_bin = partes[1].zfill(8)
                    micro_sequencia.append("00110101000001001010100") # SP=MAR=SP+1
                    micro_sequencia.append(f"{val_bin}000000000110000") # CASO ESPECIAL [cite: 226]
                    micro_sequencia.append("00111100010000001001000") # MDR=TOS=H; wr
                
                elif comando == "ILOAD": # [cite: 180, 186, 192, 196]
                    x = int(partes[1])
                    micro_sequencia.append("00111100000000001000101") # H=LV
                    for _ in range(x):
                        micro_sequencia.append("00111100000000001001000") # H=H+1
                    micro_sequencia.append("00111000100000000010000") # MAR=H; rd
                    micro_sequencia.append("00110101000001001010100") # MAR=SP=SP+1; wr
                    micro_sequencia.append("00111100000000010000000") # TOS=MDR

                elif comando == "DUP": # [cite: 212, 213, 214]
                    micro_sequencia.append("00110101000001001010100") # MAR=SP=SP+1
                    micro_sequencia.append("00111100000000010100111") # MDR=TOS; wr (B=TOS)

                for m_ins in micro_sequencia:
                    self.executar_microinstrucao(m_ins)

    def salvar_log_arquivo(self, nome_arquivo="saida.txt"):
        with open(nome_arquivo, 'w') as f:
            f.writelines(self.log_buffer)

# --- EXECUÇÃO DO PROJETO ---
if __name__ == "__main__":
    cpu = Mic1Completa()
    
    # Arquivos conforme o enunciado do projeto
    arq_regs = "registradores.txt"
    arq_mem  = "dados.txt"
    arq_inst = "instrucoes.txt"
    arq_saida = "saida.txt"

    print("--- Iniciando Simulação Mic-1 ---")

    # Verifica se os arquivos existem antes de tentar ler
    for arq in [arq_regs, arq_mem, arq_inst]:
        if not os.path.exists(arq):
            print(f"ERRO: Arquivo '{arq}' não encontrado na pasta {os.getcwd()}")
        else:
            print(f"OK: Arquivo '{arq}' detectado.")

    # 1. Carrega Estados Iniciais
    cpu.reset_registradores(arq_regs)
    cpu.reset_memoria(arq_mem)
    
    # 2. Executa a tradução e processamento
    print(f"Lendo instruções de {arq_inst}...")
    cpu.traduzir_e_executar(arq_inst)
    
    # 3. Finaliza e grava o log
    if cpu.log_buffer:
        cpu.salvar_log_arquivo(arq_saida)
        print(f"SUCESSO: Log gerado com {len(cpu.log_buffer)} microinstruções em '{arq_saida}'.")
    else:
        print("AVISO: O log está vazio. Verifique se o arquivo 'instrucoes.txt' contém comandos válidos (BIPUSH, DUP, ILOAD).")