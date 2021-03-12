import React, { Component } from "react";

import { getSessionCSRF } from './../utils/session';

import configData from "./../config/config.json";

import { URL } from"./../utils/api";

import Table from "./../components/table.component"
import Loading from "./../components/loading.component"

import "./files.page.css"

export default class FilesPage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            files: [],
            loading : true
        }

        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        fetch(URL()+'storage/file/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            this.setState({ files : json["results"], loading : false });
        });

        this.upload = this.upload.bind(this);
    }

    upload() {
        
    }

    render() {
        return !this.state.loading ? (
            <div className="pageContent1">
                <div>
                    <input type="text" name="filter" className="form-control textbox fileUploadFilename" placeholder="filename" />
                    <input type="file" name="file" className="form-control textbox fileUploadFile" />
                    <button className="btn btn-primary btn-block button fileUpload" onClick={this.upload}>Upload</button>
                </div>
                <br/>
                <div>
                    <Table data={this.state.files} />
                </div>
            </div>
        ) : <Loading />
    }
}