<!-- coderabbit-ai-generated:v1 -->

# Continuação: restauração e boot reproduzível

## Resultado

O código da entrega anterior foi restaurado do S.zip fornecido pelo usuário, sobre a base e5636981a1c9de368f6b71e819c3dc188dfedbf4. Foram preservadas as correções de relocação, memória IOP, CD, controle e interrupções GS. Não existe ainda versão jogável ou pacote Xbox.

A ferramenta `shadow_of_the_colossus/rebuild_boot.py` reconstrói o diagnóstico inicial a partir do disco: verifica o hash do ELF, extrai símbolos absolutos do KERNEL, cria o mapa com Celosia, executa analyzer e recompiler e registra hashes dos insumos e ferramentas. Recusa destinos existentes e saídas dentro do repositório. Os logs e arquivos derivados ficam no destino externo escolhido.

## Reproduzir

Compile os tools conforme o guia do jogo. Use os tools Celosia da revisão df6b12b69e8c8c1d0012f5ac5b834ddb818bb2c2. Neste workspace eles estão em `inputs/sotc/tooling/celosia/tools`. A ferramenta executa esses scripts Python: use fontes confiáveis.

```sh
python3 shadow_of_the_colossus/rebuild_boot.py \
  --disc /caminho/disco \
  --analyzer build/validation/ps2xAnalyzer/ps2_analyzer \
  --recompiler build/validation/ps2xRecomp/ps2_recomp \
  --celosia-tools /caminho/celosia/tools \
  --output /caminho/novo-diagnostico
cmake -S . -B build/validation \
  -DPS2X_BUILD_STUDIO=OFF -DPS2X_ENABLE_FFMPEG=OFF \
  -DPS2X_ENABLE_DEBUG_UI=OFF -DPS2X_ENABLE_SCCACHE=OFF \
  -DPS2X_RUNNER_GENERATED_DIR=/caminho/novo-diagnostico/generated
cmake --build build/validation --target ps2EntryRunner -j 2
```

Esse processo gera somente o boot SCUS, sem os corpos recompilados dos módulos carregados dinamicamente. Não substitui a reconstrução combinada histórica.

## Verificação nesta continuação

- Cinco suítes IOP passaram.
- 457 casos C++ passaram.
- 47 verificações CTest de captura/cache passaram no conjunto das execuções. Na primeira execução faltava compilar o executável de 15 verificações de memória; depois da compilação, as 15 passaram.
- Os 18 testes Python anteriores foram reutilizados: mesmos arquivos e runtime.
- A nova ferramenta foi executada com o disco fornecido: 1.425 funções processadas, 1.251 recompiladas, 174 stubs, nenhum erro de geração ou decode e 100 avisos de fluxo. Uma segunda execução comprovou a recusa de sobrescrever o destino existente.
- O runner gerado compilou e carregou o ELF em Linux/Xvfb/OpenGL. O teste sem injeção manual de módulos terminou por timeout de 50 segundos (124), com amostras em PC 0x0010A950 e RA 0x0010A984. Não observou entrada em KERNEL/GAMECORE. O código gerado identifica esse ciclo em sceFsInit, junto à tentativa de bind do SID FILEIO 0x80000001. Isso orienta a próxima investigação; não prova espera permanente nem identifica sozinho a causa da ausência do servidor. Não havia dispositivo de áudio disponível.

## Próximo trabalho

Rastrear o carregamento/inicialização do FILEIO original e o registro de seu servidor RPC antes de alterar a política de bind. A política existente exige o registro real do endpoint; retornar sucesso fictício não valida o boot. Depois, reconstruir e validar os módulos carregados, corrigir a imagem e avançar o fluxo jogável.

O alvo atual foi compilado como PLATFORM_DESKTOP e GRAPHICS_API_OPENGL_33. Ainda faltam backend compatível com o console, inicialização/armazenamento/entrada/áudio, projeto e empacotamento Xbox e validação com ferramentas Windows e hardware real. Não foi gerado manifesto ou pacote que prometa compatibilidade sem essas etapas.
