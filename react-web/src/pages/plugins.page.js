import React, { Component } from "react";

import configData from "./../config/config.json";
import { URL } from"./../utils/api";

import PluginList from "./../components/pluginList.component"
import Loading from "./../components/loading.component"

import "./plugins.page.css"

export default class PluginsPage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            plugins : [],
            filter: "",
            loading : true
        }

        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        fetch(URL()+'plugins/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            this.setState({ plugins : json["results"], loading : false });
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
        return !this.state.loading ? (
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
        ) : <Loading />
    }
}