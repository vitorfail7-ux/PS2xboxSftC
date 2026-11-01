<!-- coderabbit-ai-generated:v1 -->

# Correção dos limites VIF DIRECT e da corrupção gráfica

## Resultado

O runtime passou a mostrar o diálogo de cartão de memória legível na inicialização original de Shadow of the Colossus. A causa da corrupção PATH1 observada foi localizada no parser VIF, antes da execução vetorial. O limite PATH1 de 64 KiB e suas regras de temporização permanecem preservados.

A execução verificada usa Linux, OpenGL por software e os módulos IOP originais carregados pelo fluxo do SCUS. Não demonstra execução no Xbox nem jogabilidade completa.

## Causa reproduzida

O parser guardava o número de qwords ainda esperados por um GIFtag IMAGE. Antes de ler o próximo VIFcode, consumia essa quantidade diretamente do fluxo VIF. Porém o tamanho de IMAGE pertence ao GIF; cada comando VIF DIRECT/DIRECTHL delimita separadamente os bytes encaminhados ao PATH2.

O jogo envia um DIRECT contendo somente o GIFtag, seguido de NOP e outro DIRECT contendo os pixels. A implementação anterior incluía esses oito bytes de comandos nos pixels e deixava os últimos oito bytes da imagem expostos ao decodificador VIF. Esse desalinhamento transformava dados de textura em comandos UNPACK.

Na captura investigada, o word de textura `0xecbaebb2`, no offset `0xe00c` do fluxo, era interpretado como UNPACK V4_32 de 186 vetores. Com CL=3/WL=1 e destino inicial `0x3b2`, o vetor 26 dava a volta na memória VU e copiava bytes do offset `0xe1b0` para o endereço VU zero. Esses bytes correspondem exatamente ao cabeçalho inválido observado antes da chamada de geometria. O endereço de saída resultante levava ao XGKICK de origem `0x3790`, cujo primeiro GIFtag declarava 1.052.688 bytes.

Uma comparação anterior entre emissão e primeira leitura do XGKICK mostrou o mesmo cabeçalho nos dois momentos: a corrupção já existia antes da transferência. Alterar a temporização ou aumentar sua capacidade não repararia essa origem.

A implementação de referência [PCSX2, _vifCode_Direct](https://github.com/PCSX2/pcsx2/blob/master/pcsx2/Vif_Codes.cpp) também determina o tamanho encaminhado a partir do imediato do DIRECT, independentemente do NLOOP do GIFtag.

## Reparo e contrato

A continuação IMAGE agora é consumida somente dentro do payload de um DIRECT/DIRECTHL. Cada comando mantém seu tamanho declarado; VIFcodes intermediários continuam executando. Se a imagem termina antes do payload, os qwords restantes são tratados como um novo GIFtag. A quantidade pendente pode persistir entre chamadas do parser.

Dois exemplos sintéticos existentes declaravam DIRECT de um/três qwords e forneciam dois/quatro qwords, esperando que os dados excedentes fossem aceitos como imagem. Esses exemplos contradiziam a delimitação por DIRECT. Os tamanhos declarados foram corrigidos para dois/quatro; suas verificações completas de pixels permanecem. Uma nova regressão independente cobre o comportamento que o jogo exige: IMAGE dividida entre DIRECTs, NOP e UNPACK intermediários, MARK posterior, continuação em outro buffer e um novo GIFtag após os pixels. A mesma sequência é exercitada com DIRECTHL.

## Verificação

- Antes do reparo de produção: 461 casos passaram e a nova regressão falhou, tanto para DIRECT quanto para DIRECTHL.
- Após o reparo: **462/462 testes Debug passaram**, incluindo VIF/GIF, visibilidade de stores e temporização XGKICK existentes.
- Reprodução do fluxo capturado com o parser anterior e as mesmas entradas: dados de textura chegaram à geometria; ocorreu o mesmo estouro de origem `0x3790` e tamanho 1.052.688. O diagnóstico encerrou deliberadamente após 21 paradas VU.
- Reprodução com o parser corrigido, as mesmas entradas e callbacks VU/GS reais: **4.755 chamadas vetoriais, 1.814.528 ciclos, nenhuma parada VU e nenhum cabeçalho de textura passado à geometria**. Essa é uma reprodução de comandos capturados, não uma nova execução completa do jogo.
- Runtime otimizado recompilado e runner ligado novamente. Os objetos gerados do jogo foram reutilizados: as fontes e interfaces públicas permaneceram iguais. A única declaração de header pendente da revisão anterior era um método privado sem alteração de layout; a compatibilidade do objeto VU foi conferida na reprodução isolada.

### Execução original

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:c3c3e61baafd6c13d22ba1fb6d155560359903e5d9539914c3b76def80db7be9 -->

A execução do SCUS original completou o diagnóstico com saída 0 do GDB após SIGINT e encerramento deliberados. Down/X e depois Enter/X foram entregues normalmente pelo controle, sem alterar flags ou RAM convidada. As capturas mostram o aviso do cartão e as opções Retry/Continue legíveis; após a seleção, aparece a apresentação “Sony Computer Entertainment America Presents”.

No ponto final: conclusão do cartão `1`, contador GP `408`, contador GP do KERNEL `479`, VU em `77.876.801` ciclos, `m_stopRequested=false`. Não ocorreu log de estouro PATH1 nem de opcode VU reservado nessa execução. Esses contadores são observações pontuais, não uma medida de FPS.

A última captura, após Enter/X e mais 45 segundos de espera, mostra uma área cinza sobre preto. Não foi demonstrado título legível, cenário 3D ou controle jogável. O fluxo gráfico segue ativo no ponto amostrado, mas a próxima cena precisa ser investigada separadamente. A configuração estava com FFmpeg desativado; nenhum aviso de alimentação do decoder MPEG apareceu no log, portanto a tela cinza não foi atribuída ao decoder sem evidência.

O runtime/testes e o fluxo capturado usam o mesmo reparo. Cinco suítes IOP, 47 verificações de captura/cache e 18 testes Python anteriores foram reutilizados porque os insumos relevantes não mudaram. As nove referências locais da documentação e `git diff --check` passaram.

<!-- /coderabbit-ai-generated:v1 -->

## Limites e continuidade

Os comandos DIRECT completos presentes no fluxo capturado foram verificados. Fragmentação arbitrária de um comando DIRECT entre buffers, outros formatos GIF e outras revisões do jogo não foram demonstrados por esse diagnóstico.

Dados do disco, streams gráficos, RAM, executável e corpos recompilados permanecem fora do Git. A captura visual é disponibilizada nos Outputs da tarefa. Backend/projeto compatíveis com Xbox, empacotamento, SDK Windows e validação no console continuam necessários; este reparo não entrega um pacote Xbox.
