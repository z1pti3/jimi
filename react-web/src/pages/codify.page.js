import React, { Component } from "react";

import configData from "../config/config.json";

import "./codify.page.css"

export default class CodifyPage extends Component {
    constructor(props) {
        super(props);
    }

    render() {
        return (
            <div className="pageContent0">
                <iframe className="codifyFrame" src={configData.url+"codify/"}></iframe>
            </div>
        );
    }
}