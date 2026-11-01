<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:38db7624d00ded02ea637b56ccf80417de128cdc2f8a372f8519ef67531d8282 -->

<!-- coderabbit-ai-generated-section:v1:f6a3b8e8aa023b13968f60ecf7b528573f86e302780b2fca537cc87696a6c41b -->

# Inicialização com módulos originais do disco

## Avanço verificado

O SCUS original passou a executar KERNEL, MANAGER e GAMECORE (`0x01344788`) sem injeção manual de FILEIO, LIBSD ou SG2IOPM1. O GAMECORE inicializa callbacks de vídeo, encontra NICO.DAT e entra na rotina de verificação do cartão de memória. A execução ainda usa corpos C++ recompilados a partir de capturas dos módulos relocados. Isso verifica uma etapa de inicialização em Linux; não demonstra jogo jogável ou execução no Xbox.

## Reparos

1. `sceSifRebootIop` ignorava a imagem solicitada e somente apagava o IOP. Agora resolve o caminho pelo VFS, valida a imagem ROMDIR antes do reset e inicia os IRXs FILEIO, LOADFILE e CDVDFSV originais. O formato suportado tem RESET vazio e ROMDIR no início. Outros formatos/imagens sem esses serviços são rejeitados. Os imports de kernel continuam fornecidos pelo IOP virtual: este é um bootstrap parcial dos serviços, não a emulação completa do reboot de hardware.
2. `sceSifLoadModuleBuffer` lia o endereço na RAM EE. A API recebe o destino IOP depois de DMA; a correção lê a RAM IOP e encaminha os argumentos ao carregador físico. O identificador do módulo também passa a derivar desses bytes. A API pública auxiliar `loadIopModuleBuffer` mantém sua conveniência de carregar um buffer EE.
3. CDVDFSV chamava `cdvdman:47` sem implementação. `sceGetFsvRbuf` agora retorna uma região IOP compartilhada de 42.128 bytes, com endereço estável até o reset.

A política de bind exige o servidor real. Falhas não criam endpoints HLE só por causa do nome do arquivo. A nova API de imagem usa o mesmo carregador ELF/IRX existente e conserva registro/remoção dos servidores físicos.

Referências primárias: [sequência de reboot](https://github.com/ps2dev/ps2sdk/blob/master/ee/kernel/src/iopcontrol.c), [SifExecModuleBuffer e DMA](https://github.com/ps2dev/ps2sdk/blob/master/ee/kernel/src/loadfile.c), [buffer CDVDFSV](https://github.com/ps2dev/ps2sdk/blob/master/iop/cdvd/cdvdman/src/cdvdman.c).

## Reconstrução por etapas

Primeiro gere o boot inicial com `rebuild_boot.py`, conforme o relatório anterior. Compile e execute o runner com o SCUS original e `PS2X_CAPTURE_MISSING_DIR` apontando a um diretório externo novo. Quando faltar o corpo da entrada do KERNEL, o runtime salva `ram.bin` e `target.txt`. Encerre o diagnóstico após a captura.

Use Celosia da revisão `df6b12b69e8c8c1d0012f5ac5b834ddb818bb2c2` e seus scripts confiáveis:

```sh
python3 shadow_of_the_colossus/rebuild_modules.py \
  --disc /caminho/disco \
  --boot /caminho/boot-inicial \
  --recompiler build/validation/ps2xRecomp/ps2_recomp \
  --celosia-tools /caminho/celosia/tools \
  --kernel-ram /caminho/captura-kernel/ram.bin \
  --output /caminho/novo-kernel
cmake -S . -B build/validation \
  -DPS2X_RUNNER_GENERATED_DIR=/caminho/novo-kernel/generated
cmake --build build/validation --target ps2EntryRunner -j 4
PS2X_CAPTURE_MISSING_DIR=/caminho/captura-manager \
  build/validation/ps2xRuntime/ps2EntryRunner /caminho/disco/SCUS_974.72
```

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:6358e753220bdd6dc54cb1b4b3acd99c85e7cf76e362d7a44573f53bb2d830e9 -->

Repita a geração em outro destino incluindo `--manager-ram /caminho/captura-manager/ram.bin`. Após compilar, execute novamente o SCUS para capturar a entrada do GAMECORE. Finalmente gere outro destino com as três opções `--kernel-ram`, `--manager-ram` e `--gamecore-ram` e compile esse `generated/`.

Para diagnósticos prolongados, desative `PS2X_ENABLE_AGRESSIVE_LOGS` na configuração CMake. O trace por função produziu cerca de 145 MiB em uma única execução limitada e dificulta observar o progresso. A configuração Debug sem esse trace também avançou lentamente; tempo de execução no host não equivale a tempo de jogo emulado.

<!-- /coderabbit-ai-generated:v1 -->

A ferramenta recusa destinos existentes ou dentro do repositório, exige capturas EE completas de 32 MiB e verifica o SHA256 do SCUS suportado. Registra hashes dos módulos, capturas, ferramentas e configuração em `manifest.json`, junto com os logs da combinação/recompilação. As capturas determinam endereços do diagnóstico: não oferecem tratamento geral de qualquer disposição dinâmica dos módulos.

## Verificação

- 460/460 testes C++ passaram. Cobrem imagens malformadas, falha de reboot sem descartar módulos ativos e distinção entre buffers EE/IOP.
- Cinco suítes IOP passaram, incluindo registro/remoção de RPC por IRX carregado em bytes, rejeição de imagem inválida e persistência/reset do buffer CDVDFSV.
- As 47 verificações isoladas de captura/cache e os 18 testes Python anteriores foram reutilizados, sem mudanças em seus insumos relevantes.
- Reconstrução KERNEL/MANAGER: 5.052 funções processadas, 4.864 recompiladas, 188 stubs, 510 avisos, nenhum erro de geração ou decode. O runner compilou.
- Reconstrução com os três módulos: 9.024 funções processadas, 8.836 recompiladas, 188 stubs, 670 avisos, nenhum erro de geração ou decode. As 26.624 referências importadas configuradas usam leitura dos campos relocados em memória. O runner compilou com esse conjunto.
- Execução do SCUS original com GAMECORE compilado: alcançou `initgcmaingp`, callbacks de quadro/fim de quadro e `st_mcBootChk`. Uma execução Debug sem trace por função foi limitada a 300 segundos (saída 124). Nenhuma função faltante foi capturada; a imagem continuou preta com indicador de carregamento. Isso não comprova renderização correta nem jogabilidade.
- A última captura dessa execução Debug registrou contador GP do KERNEL em 72 e contador de callback do jogo em 1. A rotina do cartão estava esperando a variável de prontidão `0x014664c4`. A execução otimizada posterior superou essa espera, como descrito abaixo. Os contadores são observações pontuais, não uma medida de FPS.
- O GDB confirmou que a remoção da thread de inicialização 6 é solicitada pelo próprio jogo. Esse encerramento não foi tratado como defeito do escalonador. Os diagnósticos foram de leitura, sem forçar flags ou modificar RAM convidada.

Os logs e capturas ficam em `inputs/sotc/runs/`, fora do Git. Nenhum arquivo do disco ou corpo recompilado do jogo é incluído no commit.

## Execução otimizada e falha gráfica seguinte

Uma configuração separada Release com `-O1 -DNDEBUG`, trace por função desligado e os mesmos módulos gerados compilou. Os 460 testes C++ passaram novamente nessa configuração. FFmpeg, Studio e debug UI estavam desativados; a execução usou OpenGL por software, sem áudio disponível.

O SCUS original foi executado em Xvfb sob GDB, com limite de 360 segundos (saída 124). Foram observadas `stagemanager_loadstagecore`, `initlayout` e `bootmccheck`. A prontidão `0x014664c4` passou a 1 e o diálogo do cartão atingiu o estado 2. Entradas normais de teclado correspondentes a **baixo e X**, mantidas por cinco segundos cada para atravessar os quadros lentos do diagnóstico, fizeram a conclusão `0x011e0158` passar a 1. Nenhuma flag ou RAM do convidado foi modificada pelo debugger. Enter e X posteriores não comprovaram mudança de cena.

A imagem passou do indicador de carregamento para fragmentos de texto e faixas claras sobre preto. A leitura direta da VRAM confirmou esses fragmentos no framebuffer exibido; não foi demonstrado menu legível ou cenário. O processamento GP avançou após a seleção, mas deixou de avançar nas últimas capturas enquanto surgiam erros VU1.

Um breakpoint identificou que `instruction=0xfffffffb` é o sinal interno do limite de acumulação PATH1/XGKICK. Não representa uma instrução VU desconhecida: a instrução real naquele PC era diferente e a geração do cache correspondia à memória. A captura de 1.600 bytes do pacote mostrou um novo GIFtag após 1.584 bytes, declarando um payload maior que a capacidade restante de 64 KiB. A origem VU era o offset 16.192. A causa dos campos incorretos ou do pacote excessivo ainda não foi determinada entre a produção dos dados e o processamento VIF/VU. Aumentar o limite não constitui uma correção comprovada.

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:667eb2257d52ba46761be7e3e446cb9a15fd7c2e106a4aae1b6cac3fb3a7b602 -->

Esse é o próximo bloqueio reproduzido. A execução otimizada demonstra que a espera inicial do cartão não era permanente e confirma a entrega de entrada pelo fluxo original; não estabelece jogabilidade.

### Diagnóstico explícito de capacidade PATH1

A proteção agora registra `[VU1 PATH1 overflow]`, com PC, ciclo, endereço de origem VU, último qword copiado, bytes copiados, tamanho requerido e capacidade. Os dois caminhos de estouro deixam de reportar a instrução sintética `0xfffffffb`. O limite de 64 KiB, a interrupção do processamento e a rejeição do pacote incompleto permanecem iguais. Essa alteração corrige a identificação da falha; não corrige sua origem nem a imagem.

Um teste novo declara um pacote PACKED de 8.388.368 bytes e verifica que nenhum pacote incompleto chega ao GS e que o log identifica tamanho/capacidade sem alegar instrução desconhecida. A suíte Debug passou 461/461, incluindo os testes existentes de temporização PATH1 e visibilidade de stores. A execução nativa em paralelo usou o executável otimizado anterior; não foi uma validação do novo executável do jogo.

<!-- /coderabbit-ai-generated:v1 -->

## Xbox e limitações

O alvo verificado é desktop Linux com OpenGL 3.3 e Xvfb, sem dispositivo de áudio. Ainda faltam renderização/fluxo jogável, backend e projeto compatíveis com Xbox, pacote e validação com SDK Windows e console real. Não existe pacote Xbox entregue por este avanço.


<!-- /coderabbit-ai-generated:v1 -->