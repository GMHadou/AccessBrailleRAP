import React, { Component } from "react";
import { HashRouter, Routes, Route } from 'react-router-dom';

import Layout from './layout'
import BrailleView from './pages/brailleview';
import TextInput from './pages/textinput'
import Parameters from "./pages/parameters";
import './App.css';

import AppOption from "./pages/components/AppOption";
import libLouis from "./modules/libLouisReact";
import { FormattedMessage } from "react-intl";
import { IntlContext } from './components/intlwrapper.js';


class App extends Component {
  static contextType = IntlContext;

    constructor(props)
    {
        super(props);
        //eel.set_host("ws://localhost:8888");
        //eel.hello();
        this.state= (
            {
                logstr : '',
                srctxt : '',
                options : AppOption,
                serialstatus:0,
                louisloaded:false,
                webviewready:false
            }
        );
        this.LogCallBack = this.LogCallBack.bind(this);
        this.SetText = this.SetText.bind(this);
        this.SetNbLine = this.SetNbLine.bind(this);
        this.SetNbCol = this.SetNbCol.bind(this);
        this.SetComPort = this.SetComPort.bind(this);
        this.SetOption = this.SetOption.bind(this);
        this.onMenuClick = this.onMenuClick.bind (this);    
        this.GetLouis = this.GetLouis.bind(this);
        this.LouisLoaded = this.LouisLoaded.bind (this);
        this.webviewloaded = this.webviewloaded.bind(this);
        this.focusReference = React.createRef();
    }

    async webviewloaded ()
    {
      // Evita múltiplas inicializações
      if (this.state.webviewready) {
        console.log("webviewloaded já foi chamado, ignorando");
        return;
      }
      
      if (!window.pywebview || !window.pywebview.api) {
        console.log("pywebview.api ainda não está disponível, aguardando...");
        return;
      }
      
      if (!window.pywebview.state) {
        window.pywebview.state = {};
      }
      
      console.log ("pywebviewready event - inicializando app");
      
      try {
        let option = await window.pywebview.api.gcode_get_parameters();
        console.log ("Parâmetros recebidos:", option);
        let params = JSON.parse(option);

        this.setState({webviewready:true});
        console.log (navigator.language);
        if (params.lang === "")
        {
            params.lang = "fr";
            this.SetOption (params);
        }
        else
          this.setState ({options:params})
        this.context.setLanguage (params["lang"]);
        this.context.setTheme(params["theme"]);
        this.louis = new libLouis();
        this.louis.load (this.LouisLoaded);
      } catch (error) {
        console.error("Erro ao inicializar webview:", error);
      }
    }
    async componentDidMount ()
    {
      // Verifica se pywebview já está pronto (evento pode ter sido disparado antes do mount)
      if (window.pywebview && window.pywebview.api) {
        console.log("pywebview já está disponível, verificando se precisa inicializar");
        // Pequeno delay para garantir que tudo está pronto
        setTimeout(() => {
          if (!this.state.webviewready) {
            console.log("Chamando webviewloaded diretamente");
            this.webviewloaded();
          }
        }, 100);
      }
      
      // Também aguarda o evento caso ainda não tenha sido disparado
      window.addEventListener('pywebviewready', this.webviewloaded);
      // Algumas versões do pywebview usam _pywebviewready
      window.addEventListener('_pywebviewready', this.webviewloaded);
    }

    onMenuClick ()
    {
        if (this.focusReference && this.focusReference.current) {
          this.focusReference.current.focus();
        }
    }
   
    SetText (str)
    {
      this.setState ({srctxt :str});
    }
    SetNbLine (nbline)
    {
      this.setState ({nbline :nbline});
    }
    SetNbCol (nbcol)
    {
      this.setState ({nbcol:nbcol});
    }
    SetComPort (comport)
    {
      this.setState ({comport:comport});
    }
    SetOption (opt)
    {
      console.log ("theme received " + opt.theme.toString());
      console.log ("option received " + opt.toString());
      this.setState ({option:opt});
      window.pywebview.api.gcode_set_parameters (opt);
    }
    SetStatus (status)
    {
      this.setState({serialstatus: status})
    }
    LogCallBack (str)
    {
      this.setState ({logstr : this.state.logstr + str + '\r\n'});

    }
    LouisLoaded (success)
    {
      this.setState({louisloaded:success});
    }
    GetLouis()
    {
      return this.louis;
    }
    render ()
    {
      if (! this.state.webviewready)
        return (
        <h1>
          <FormattedMessage id="app.loading" defaultMessage="Waiting webview..."/>
        </h1>);

      if (! this.state.louisloaded)
        return (
        <h1>
          <FormattedMessage id="app.loading" defaultMessage="Chargement..."/>
        </h1>);

      return (
      
        <HashRouter>
            <Routes >
              <Route path="/" element={<Layout focuscb={this.onMenuClick} status={this.state.serialstatus}/>}>
                <Route index element={<TextInput logger={this.LogCallBack} src={this.state.srctxt} textcb={this.SetText} options={this.state.options} focusref={this.focusReference}/> } />
                <Route path="/impression" element={<BrailleView logger={this.LogCallBack} src={this.state.srctxt} glouis={this.GetLouis}
                    options={this.state.options} focusref={this.focusReference} statuscb={this.SetStatus}/>} />
                <Route path="/parametre" element={<Parameters logger={this.LogCallBack} src={this.state.srctxt} glouis={this.GetLouis}
                   options={this.state.options} nblinecb={this.SetNbLine} nbcolcb={this.SetNbCol} comportcb={this.SetComPort} optioncb={this.SetOption} focusref={this.focusReference}/> } />

                <Route path="*" element={<TextInput logger={this.LogCallBack} src={this.state.srctxt} textcb={this.SetText} options={this.state.options} focusref={this.focusReference}/>} />
              </Route>
            </Routes>
          </HashRouter>
      
      );
    }
}

export default App;
