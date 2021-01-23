import React, { Component } from "react";

import configData from "./../config/config.json";

import "./plugin.page.css"

export default class PluginPage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            location : ""
        }

        const search = props.location.search;
        const pluginName = new URLSearchParams(search).get('pluginName');
        if (/^[A-Za-z]+$/.test(pluginName)) {
            this.state.location = pluginName;
        }
    }

    render() {
        return (
            <div className="pageContent0">
                <iframe className="pluginFrame" src={configData.url+"plugin/"+this.state.location+"/"}></iframe>
            </div>
        );
    }
}