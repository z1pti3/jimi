import React, { Component } from "react";

import configData from "./../config/config.json";

import "./conduct.page.css"

export default class ConductPage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            location : ""
        }

        const search = props.location.search;
        const conductID = new URLSearchParams(search).get('conductID');
        if (/^[A-Za-z0-9]+$/.test(conductID)) {
            this.state.location = conductID;
        }
    }

    render() {
        return (
            <div className="pageContent0">
                <iframe className="conductFrame" src={"/conductEditor/?conductID="+this.state.location}></iframe>
            </div>
        );
    }
}