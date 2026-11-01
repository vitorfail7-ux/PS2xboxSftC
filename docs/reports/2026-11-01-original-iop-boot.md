<!-- coderabbit-ai-generated:v1 -->

# Inicialização com módulos originais do disco

## Avanço verificado

O SCUS original passou a carregar KERNEL e MANAGER e chegou à entrada do GAMECORE (`0x01344788`) sem injeção manual de FILEIO, LIBSD ou SG2IOPM1. A execução ainda usa corpos C++ recompilados a partir de capturas dos módulos relocados. Isso verifica uma etapa de inicialização em Linux; não demonstra jogo jogável ou execução no Xbox.

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

Repita a geração em outro destino incluindo `--manager-ram /caminho/captura-manager/ram.bin`. Após compilar, execute novamente o SCUS para capturar a entrada do GAMECORE. Finalmente gere outro destino com as três opções `--kernel-ram`, `--manager-ram` e `--gamecore-ram` e compile esse `generated/`.

A ferramenta recusa destinos existentes ou dentro do repositório, exige capturas EE completas de 32 MiB e verifica o SHA256 do SCUS suportado. Registra hashes dos módulos, capturas, ferramentas e configuração em `manifest.json`, junto com os logs da combinação/recompilação. As capturas determinam endereços do diagnóstico: não oferecem tratamento geral de qualquer disposição dinâmica dos módulos.

## Verificação

- 460/460 testes C++ passaram. Cobrem imagens malformadas, falha de reboot sem descartar módulos ativos e distinção entre buffers EE/IOP.
- Cinco suítes IOP passaram, incluindo registro/remoção de RPC por IRX carregado em bytes, rejeição de imagem inválida e persistência/reset do buffer CDVDFSV.
- As 47 verificações isoladas de captura/cache e os 18 testes Python anteriores foram reutilizados, sem mudanças em seus insumos relevantes.
- Reconstrução KERNEL/MANAGER: 5.052 funções processadas, 4.864 recompiladas, 188 stubs, 510 avisos, nenhum erro de geração ou decode. O runner compilou.
- Execução do SCUS original: KERNEL e MANAGER executados, GAMECORE carregado e entrada alcançada. O processo foi encerrado com TERM após salvar a captura; não foi saída normal do jogo.

Os logs e capturas ficam em `inputs/sotc/runs/`, fora do Git. Nenhum arquivo do disco ou corpo recompilado do jogo é incluído no commit.

## Xbox e limitações

O alvo verificado é desktop Linux com OpenGL 3.3 e Xvfb, sem dispositivo de áudio. Ainda faltam renderização/fluxo jogável, backend e projeto compatíveis com Xbox, pacote e validação com SDK Windows e console real. Não existe pacote Xbox entregue por este avanço.
