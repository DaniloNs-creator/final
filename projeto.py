# Na função main(), substitua esta parte:

# Gerar XML
with st.spinner("Gerando XML no formato exato..."):
    # Use a nova função que processa todos os itens
    xml_content = create_xml_with_all_items(dados)
    
    # Mostrar estatísticas
    st.success(f"✅ Encontrados {len(dados['itens'])} itens no PDF")
    
    # Mostrar resumo dos itens em uma tabela
    if dados.get('itens'):
        st.subheader(f"📊 Resumo dos {len(dados['itens'])} Itens")
        
        # Criar DataFrame resumido
        resumo_items = []
        for item in dados['itens'][:20]:  # Mostrar apenas os primeiros 20
            resumo_items.append({
                "Item": item.get('numero', ''),
                "NCM": item.get('ncm', ''),
                "Descrição": item.get('descricao', '')[:50] + "..." if len(item.get('descricao', '')) > 50 else item.get('descricao', ''),
                "Qtd": item.get('qtde_unid_comercial', ''),
                "Valor Unit": item.get('valor_unit_cond_venda', ''),
                "II": item.get('ii_valor_calculado', ''),
                "IPI": item.get('ipi_valor_calculado', '')
            })
        
        if resumo_items:
            df_resumo = pd.DataFrame(resumo_items)
            st.dataframe(df_resumo, use_container_width=True)
        
        if len(dados['itens']) > 20:
            st.info(f"Mostrando 20 de {len(dados['itens'])} itens. Verifique o XML completo para todos os itens.")
