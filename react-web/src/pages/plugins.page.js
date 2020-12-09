import React, { Component } from "react";

import configData from "./../config/config.json";

import PluginList from "./../components/pluginList.component"

export default class Plugins extends Component {
    constructor(props) {
        super(props);
        this.state = {
            plugins : []
        }

        const requestOptions = {
            method: 'GET',
            credentials: 'include',
            mode: configData.cosMode
        };
        fetch(configData.url+configData.uri+'plugins/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            this.setState({ plugins : json["results"] });
        });
    }

    render() {
        return (
            <div className="pageContent1">
                <PluginList plugins={this.state.plugins} />
            </div>
        );
    }
}