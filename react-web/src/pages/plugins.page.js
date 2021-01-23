import React, { Component } from "react";

import configData from "./../config/config.json";

import PluginList from "./../components/pluginList.component"

import "./plugins.page.css"

export default class PluginsPage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            plugins : [],
            filter: ""
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

        this.change = this.change.bind(this);
    }

    change(event) {
        const target = event.target;
        var value = target.value;
        const name = target.name;
        if (target.type === 'checkbox') {

        } else {
            this.setState({ [name]: value });
        }   
    }

    render() {
        return (
            <div className="pageContent1">
                <div>
                    <input type="text" name="filter" className="form-control textbox pluginSearch" placeholder="Search Plugins" onChange={this.change} />
                </div>
                <br/>
                <div className="pageCenter-outer">
                    <div className="pageCenter-inner">
                        <PluginList plugins={this.state.plugins} filter={this.state.filter} />
                    </div>
                </div>
            </div>
        );
    }
}