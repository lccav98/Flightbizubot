# Governança JEV — Flightbizubot

Estas instruções se aplicam a todo o repositório. Priorize capacidade,
precisão, robustez técnica e adequação à tarefa acima de preço, velocidade
ou provedor. Preserve o modelo explicitamente escolhido e o esforço pedido.

## Fluxo obrigatório quando o MCP JEV estiver disponível

1. No início de uma tarefa complexa, chame `jev_route_task` com o objetivo
   e 1–3 linhas de evidência recente. Dispense a chamada em confirmações e
   follow-ups diretos sem nova tarefa. Respeite `proceed_fast`, `deep_review`,
   `split_task` ou `block`; resolva dúvidas já respondidas pelo contexto.
2. Leia o código e as instruções antes de editar. Use `jev_decide` para
   decisões estruturadas relevantes, com critérios explícitos de capacidade.
3. Antes de editar/deletar arquivos ou executar ações consequentes, use
   `jev_guard_tool_call`. Não use para leituras. `allow`: prossiga;
   `review`: aprofunde a análise; `deny`: não execute; `confirm`: solicite
   confirmação, salvo autorização explícita já existente para a mesma ação.
4. Em `split_task`, valide escopos isolados em `jev_delegate_subagent` antes
   de delegar pelas ferramentas reais do host. Evite escritores concorrentes.
   Essa ferramenta valida a proposta; ela não cria subagentes por si só.
5. Em trabalhos longos ou retomadas, use `jev_memory_sync` com caminho
   absoluto deste checkout em `.jev/state.json`. Não salve tokens, conteúdo
   de `.env`, dados de assinantes nem logs privados. Confira o estado salvo
   contra o código atual antes de confiar em verificações antigas.
6. Use `jev_check_research` quando uma conclusão depender de evidências
   externas ou alegações incertas. Forneça evidências reais, sem inventá-las.
7. Execute `python -W error scripts/validate.py`. Para mudanças lógicas,
   acrescente verificações comportamentais pertinentes e passe comando,
   saída real e código de saída a `jev_verify_tests` com `strict=true`.
   A ferramenta analisa resultados; não executa testes. Falhas e warnings
   não tratados impedem declarar validação aprovada.
8. Consulte `jev_metrics` para auditoria. Não registre duas vezes uma rota
   que já retornou `metrics_recorded=true`; não fabrique economia de tokens.
   Use caminho absoluto em `.jev/metrics.json` quando necessário.
9. Antes de concluir, chame `jev_review_completion` com critérios de aceite,
   trabalho realizado, testes e limitações. Investigue `verify_more`; relate
   o que permanece pendente em `incomplete`.

## Validação e segurança do projeto

- A checagem offline compila fontes sem importar o bot e roda testes SQLite
  em diretório temporário, com configuração fictícia. Não precisa de `.env`,
  dependências de produção ou credenciais. Não prova acesso a provedores,
  funcionamento do Telegram ou operação 24/7.
- Não execute `main.py`, scheduler, scripts de startup, Docker Compose ou
  varreduras reais para validar uma alteração. Não envie mensagens pelo
  Telegram sem autorização explícita para esse envio.
- Nunca leia/exponha credenciais para diagnóstico. Nunca versione `.env`,
  tokens, bancos de produção, chat IDs reais ou arquivos locais de `.jev`.
- Não altere regras de alertas, rotas, banco ou deployment fora do escopo.
  Testes de banco devem usar arquivos temporários e fechar conexões.
- Não afirme que o JEV intercepta todas as ferramentas ou troca o modelo do
  Codex. O MCP precisa estar instalado e conectado no ambiente do agente.

## Se o JEV estiver indisponível

Informe a indisponibilidade e siga manualmente o mesmo rigor: leia, planeje,
avalie riscos, valide e relate limites. Não simule chamadas ou aprovação JEV.
A CI offline deve continuar funcionando sem acesso ao JEV. Consulte
[docs/JEV.md](docs/JEV.md) para operação e critérios de aceite.
